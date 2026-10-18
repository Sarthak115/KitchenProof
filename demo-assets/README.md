# Demo assets

The team's sample kitchen videos live in `frontend/public/demo/` so Firebase Hosting can serve them
for playback. `scripts/upload_demo_assets.py` copies them to `gs://$STORAGE_BUCKET/demo-assets/`
so Gemini on Vertex AI can read them. The backend loads each video's instruction timeline from
`backend/app/demo/timelines/*.json` (Cloud Run builds only the `backend/` folder).

| Video | Length | Timeline (seconds) | Content |
|---|---|---|---|
| `messy_kitchen.mp4` | 93 s | fridge 0 · sink 21 · dustbin 30 · ✋ 5 fingers at the stove 39 · board/counter 54 · labels 77 | uncovered food in the fridge, dishes in the sink, open waste bag, stained board, expired ghee |
| `clean_kitchen.mp4` | 72 s | fridge 0 · sink 15 · dustbin 24 · stove 33 · ✋ 3 fingers at the stove 39 · shelves 51 · labels 60 | same kitchen after fixing the problems |
| `too_perfect_kitchen.mp4` | — | not recorded | the demo uses an example result for this sample |

`backend/app/demo/cached_results/` holds gemini-3.8-flash's real output for the recorded videos.
It is shown (with a "cached result" note) only if Gemini is unavailable during a demo.
