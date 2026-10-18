#!/usr/bin/env bash
# Deploy KitchenProof to Google Cloud (Cloud Run + Firebase Hosting). Run from the repo root in
# Google Cloud Shell:   bash scripts/deploy.sh
# Safe to re-run: each step skips or updates what already exists.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-kitchenproof}"
REGION="${REGION:-asia-south1}"
BUCKET="${BUCKET:-kitchenproof.firebasestorage.app}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"
# Optional: your real kitchen's location for live camera demos, as "lat;lng"
DEMO_KITCHEN_LATLNG="${DEMO_KITCHEN_LATLNG:-}"
SA="kitchenproof-api@${PROJECT_ID}.iam.gserviceaccount.com"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

step "1/8 Project"
gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
echo "project $PROJECT_ID ($PROJECT_NUMBER), region $REGION, bucket $BUCKET"

step "2/8 Enable Google Cloud APIs (takes a minute the first time)"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com aiplatform.googleapis.com storage.googleapis.com \
  secretmanager.googleapis.com cloudscheduler.googleapis.com firebasehosting.googleapis.com

step "3/8 Service account for the API"
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 \
  || gcloud iam service-accounts create kitchenproof-api --display-name "KitchenProof API"
for role in roles/aiplatform.user roles/datastore.user roles/storage.objectViewer roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$SA" --role "$role" \
    --condition=None >/dev/null
done
# Gemini on Vertex AI reads the videos from Cloud Storage through the Vertex AI service agent
gcloud beta services identity create --service=aiplatform.googleapis.com >/dev/null 2>&1 || true
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role roles/storage.objectViewer >/dev/null
echo "permissions ok"

step "4/8 Secrets"
for name in admin-secret scheduler-secret; do
  gcloud secrets describe "$name" >/dev/null 2>&1 \
    || printf '%s' "$(openssl rand -hex 16)" | gcloud secrets create "$name" --data-file=- >/dev/null
done
echo "admin-secret and scheduler-secret exist (read one with: gcloud secrets versions access latest --secret admin-secret)"

step "5/8 Upload sample kitchen videos for Gemini"
gcloud storage cp frontend/public/demo/*.mp4 "gs://$BUCKET/demo-assets/"

step "6/8 Deploy the API to Cloud Run (builds the container; 3-5 minutes)"
gcloud run deploy kitchenproof-api --source backend --region "$REGION" \
  --service-account "$SA" --allow-unauthenticated --timeout 300 --memory 1Gi --no-cpu-throttling \
  --min-instances 0 --max-instances 3 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=$GEMINI_MODEL,GEMINI_FALLBACK_MODEL=gemini-3.5-flash,DEMO_MODE=true,STORAGE_BUCKET=$BUCKET,CUSTOMER_CHECKS_PER_DAY=25,DEMO_KITCHEN_LATLNG=$DEMO_KITCHEN_LATLNG" \
  --set-secrets "SCHEDULER_SECRET=scheduler-secret:latest,ADMIN_SECRET=admin-secret:latest"

step "7/8 Build the web app"
(cd frontend && npm ci --no-audit --no-fund && npm run build)

step "8/8 Deploy Firebase Hosting + security rules"
npx --yes firebase-tools@13.29.1 deploy --project "$PROJECT_ID" \
  --only hosting,firestore:rules,firestore:indexes,storage --non-interactive

URL="https://${PROJECT_ID}.web.app"
step "Done"
echo "App:    $URL"
echo "Tour:   $URL/tour"
echo "Health: $(curl -s "$URL/api/health" || echo 'not answering yet, try again in a minute')"
