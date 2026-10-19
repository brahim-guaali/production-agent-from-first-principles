#!/bin/zsh
# Re-run every stage on the real model and keep its terminal output next to it (<stage>/output.txt),
# then export every traced run from the platform to viz/data/. Needs `make platform` and GEMINI_API_KEY.
set -u
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1
run() { local dir=$1; shift; echo "\$ python $dir/$*" > $dir/output.txt; .venv/bin/python "$dir/$@" >> $dir/output.txt 2>&1; }
for dir in [0-9][0-9]-*/; do run ${dir%/} run.py; done
curl -s http://127.0.0.1:8710/runs > viz/data/runs-index.json
for id in $(python3 -c "import json;print(' '.join(r['id'] for r in json.load(open('viz/data/runs-index.json'))))"); do
  curl -s "http://127.0.0.1:8710/runs/$id" > "viz/data/run-$id.json"
done
echo done
