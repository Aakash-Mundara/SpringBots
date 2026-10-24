#!/usr/bin/env bash
# Starts OnboardIQ on http://127.0.0.1:8080. Optional env: OCR_ENGINE, AI_EXTRACTION, OLLAMA_MODEL, OLLAMA_VISION_MODEL
set -euo pipefail
cd "$(dirname "$0")"
python3 -m uvicorn local_app:app --host 127.0.0.1 --port "${PORT:-8080}"
