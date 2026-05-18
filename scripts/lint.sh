#!/bin/bash
set -e
echo "Running ruff check..."
ruff check src/ tests/

echo "Running basedpyright..."
cd "$(dirname "$0")/../src/vigilancia_multiagente"
python -m basedpyright
