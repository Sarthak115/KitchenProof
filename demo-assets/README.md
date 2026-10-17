# Demo assets

The team records three 2–3 minute phone videos (720p) here, each following the fixed
instruction timeline in `backend/app/demo/timelines/*.json` (the backend loads timelines from there
because Cloud Run builds only the `backend/` folder):

| File | Timeline | Content |
|---|---|---|
| `messy_kitchen.mp4` | `messy.json` | raw chicken packet on the top shelf above cooked food, open dustbin, dirty counter |
| `clean_kitchen.mp4` | `clean.json` | same kitchen with the problems fixed |
| `too_perfect_kitchen.mp4` | `too_perfect.json` | spotless, nothing cooking, brand-new unopened packs (used with a high order count) |

Timeline (seconds from start): fridge shelves 0 · handwash 20 · dustbins 40 · **liveness 60**
(3 fingers at the stove; 2 fingers at the fridge for too-perfect) · counter & boards 75 · cook from
the shoulders down 95 · two packet labels 115 · stop at ~140.

Then run `scripts/upload_demo_assets.py`. Videos are git-ignored only if you add them to
`.gitignore`; keep each under ~50 MB if you commit them.
