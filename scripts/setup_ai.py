#!/usr/bin/env python3
"""One-time local AI setup check: downloads the RapidOCR model files (~15 MB, once) and reports
which OCR engine and local LLM (Ollama) OnboardIQ will use. Run: python scripts/setup_ai.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocr_engine

st = ocr_engine.status()
print('OCR engines available :', json.dumps(st['engines']))
eng = st['ocr_engine']
if not eng:
    print('!! No OCR engine. Run: pip install rapidocr onnxruntime   (or install Tesseract and pytesseract)'); sys.exit(1)
print('Selected OCR engine   :', eng)
from PIL import Image, ImageDraw
img = Image.new('RGB', (900, 160), 'white'); ImageDraw.Draw(img).text((20, 60), 'PERMANENT ACCOUNT NUMBER ZZKPS1234Q', fill='black')
r = ocr_engine.ocr_image(img)  # first call downloads/loads models
print('OCR self-test         :', r.text.strip() or '(empty)', f'(conf {r.confidence:.2f})')
ai = st['ai']
if ai.get('enabled'):
    print(f"Local LLM             : ON via Ollama ({ai['model']}{' + vision ' + ai['vision_model'] if ai.get('vision_model_ready') else ''})")
else:
    print('Local LLM             : off -', ai.get('reason'))
    print('  Optional: install Ollama (https://ollama.com), then:  ollama pull qwen2.5:3b')
    print('  For reading images directly with a vision model:      ollama pull qwen2.5vl:3b  and set OLLAMA_VISION_MODEL=qwen2.5vl:3b')
