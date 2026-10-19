# Visuals

Every image, GIF and video in this repo comes from a recorded run, and its caption says how it was made.

| Tool | What it does |
|---|---|
| `record_runs.sh` | Re-runs every stage on the real model, keeps each `<stage>/output.txt`, and exports traced runs to `data/` |
| `terminal.py` | Renders a stage's real `output.txt` as an image (nothing retyped) |
| `make_gif.sh` | Turns frames captured from the viewer's replay mode into a GIF and an MP4 |
| `compose.py` | Stacks two replayed timelines on one clock |
| `watermark.py` | Stamps `medium.com/@brahimg` in a thin strip under each image used in the write-up; `watermarked.txt` lists what is done |

After redrawing a stamped file, remove its line from `watermarked.txt` and run `python viz/watermark.py` again.
