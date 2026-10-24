#!/usr/bin/env bash
# Start the API for local dev. Uses the labplanner env (has Opentrons) so runs produce a
# real simulation, and restricts uvicorn --reload to the SOURCE dirs only.
#
# Why the --reload-dir flags matter: the pipeline writes generated files during a run
# (protocols/<id>.py in stage 3, database/app.db + WAL). Plain `uvicorn --reload` watches
# the whole tree, so writing protocols/<id>.py mid-run RESTARTS the server and kills the
# in-flight worker thread, leaving a run "stuck at design". Watching only backend/ and
# pipeline/ keeps generated output from triggering a reload.
set -euo pipefail

PY="${LABPLANNER_PYTHON:-/opt/homebrew/Caskroom/miniforge/base/envs/labplanner/bin/python}"

exec "$PY" -m uvicorn backend.api:app \
  --reload \
  --reload-dir backend \
  --reload-dir pipeline \
  --reload-exclude 'protocols/*' \
  --reload-exclude 'database/*' \
  --host 127.0.0.1 --port 8000
