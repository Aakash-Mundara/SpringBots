# Starts OnboardIQ on http://127.0.0.1:8080. Optional env: $env:OCR_ENGINE, $env:AI_EXTRACTION, $env:OLLAMA_MODEL, $env:OLLAMA_VISION_MODEL
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$port = if ($env:PORT) { $env:PORT } else { 8080 }
python -m uvicorn local_app:app --host 127.0.0.1 --port $port
