#!/bin/bash
# Run basedpyright type checker
set -e
cd "$(dirname "$0")/../src/vigilancia_multiagente"
python -m basedpyright "$@"
