#!/usr/bin/env python3
"""Measure local extraction accuracy against the supplied ground truth.

Modes
  --mode text   : feed the supplied OCR text (.txt) through classifier + field parsers
  --mode image  : render each document to a PNG (synthetic scan) and run real local OCR first
  --mode pdf    : render to an image-only PDF and run the PDF path (OCR of scanned pages)

Also runs the deterministic rules engine on the *real* extraction output (instead of the mock
extraction CSV) and reports how many sample decisions still match the expected decision.

  python scripts/eval_extraction.py --mode text
  python scripts/eval_extraction.py --mode image --limit 60
"""
import argparse, csv, io, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import ocr_engine  # noqa: E402
from run_batch import RulesEngine, read_csv  # noqa: E402

CHECK = ['doc_type', 'name', 'dob', 'gender', 'pan_number', 'aadhaar_last4', 'pincode', 'document_date', 'valid_until']


def render_png(text: str, noise: bool = False) -> bytes:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 30)
    except OSError:
        try:
            font = ImageFont.truetype('arial.ttf', 30)
        except OSError:
            font = ImageFont.load_default()
    lines = [l.rstrip() for l in text.splitlines()]
    w = 1500; h = 70 + 46 * len(lines)
    img = Image.new('RGB', (w, h), (250, 249, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([12, 12, w - 12, h - 12], outline=(120, 130, 150), width=3)
    y = 35
    for l in lines:
        d.text((40, y), l, fill=(25, 30, 40), font=font); y += 46
    if noise:
        img = img.rotate(0.8, expand=True, fillcolor=(250, 249, 245)).filter(ImageFilter.GaussianBlur(0.6))
    b = io.BytesIO(); img.save(b, 'PNG'); return b.getvalue()


def to_pdf(png: bytes) -> bytes:
    from PIL import Image
    b = io.BytesIO(); Image.open(io.BytesIO(png)).convert('RGB').save(b, 'PDF', resolution=150); return b.getvalue()


def norm(k, v):
    v = (v or '').strip()
    if k == 'name':
        return ' '.join(sorted(v.upper().split()))
    return v.upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['text', 'image', 'pdf'], default='text')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--ai', action='store_true', help='also call the local LLM (Ollama) if available')
    ap.add_argument('--out', default=str(ROOT / 'output' / 'extraction_eval.csv'))
    a = ap.parse_args()
    data = ROOT / 'data'
    truth = {r['doc_id']: r for r in read_csv(data / 'case_02_document_truth_sample_V1.0.csv')}
    texts = [json.loads(l) for l in open(data / 'case_02_document_text_sample_V1.0.jsonl', encoding='utf-8')]
    if a.limit:
        texts = texts[:a.limit]
    per = {k: [0, 0] for k in CHECK}; rows = []; extracted = {}; t0 = time.time()
    for d in texts:
        if a.mode == 'text':
            payload, fn = d['text'].encode(), d['doc_id'] + '.txt'
        else:
            png = render_png(d['text'], noise=True)
            payload, fn = (png, d['doc_id'] + '.png') if a.mode == 'image' else (to_pdf(png), d['doc_id'] + '.pdf')
        try:
            r = ocr_engine.extract_document(payload, fn, use_ai=a.ai)
            fields = r['fields']
        except ocr_engine.DocumentRejected as e:
            fields = {}; print('REJECTED', d['doc_id'], e)
        extracted[d['doc_id']] = fields
        t = truth.get(d['doc_id'], {})
        for k in CHECK:
            exp = t.get(k, '')
            got = fields.get(k, {}).get('value', '')
            if not exp and not got:
                continue
            ok = norm(k, exp) == norm(k, got)
            per[k][0] += ok; per[k][1] += 1
            if not ok:
                rows.append({'doc_id': d['doc_id'], 'field': k, 'expected': exp, 'got': got,
                             'confidence': fields.get(k, {}).get('confidence', '')})
    dur = time.time() - t0
    print(f'Mode={a.mode}  documents={len(texts)}  time={dur:.1f}s  ({dur / max(1, len(texts)):.2f}s/doc)')
    tot = [0, 0]
    for k, (ok, n) in per.items():
        if n:
            print(f'  {k:14s} {ok:4d}/{n:<4d} {ok / n:6.1%}')
            tot[0] += ok; tot[1] += n
    print(f'  {"ALL FIELDS":14s} {tot[0]:4d}/{tot[1]:<4d} {tot[0] / max(1, tot[1]):6.1%}')
    # wrong values that would pass the 0.80 confidence gate are the dangerous ones
    silent = [r for r in rows if r['got'] and float(r['confidence'] or 0) >= 0.8]
    print(f'  wrong values with confidence >= 0.80 (would not be flagged): {len(silent)}')
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['doc_id', 'field', 'expected', 'got', 'confidence']); w.writeheader(); w.writerows(rows)
    print(f'  mismatches written to {a.out}')

    # Decisions on real extraction instead of mock extraction
    eng = RulesEngine(data); eng.extractions = extracted
    apps = read_csv(data / 'case_02_applications_sample_V1.0.csv'); docs = read_csv(data / 'case_02_documents_sample_V1.0.csv')
    have = {d['doc_id'] for d in texts}; byapp = {}
    for d in docs:
        byapp.setdefault(d['application_id'], []).append(d)
    n = same = 0
    for app in apps:
        ds = byapp.get(app['application_id'], [])
        if not ds or not all(x['doc_id'] in have for x in ds):
            continue
        res = eng.evaluate(app, ds); n += 1; same += res['decision'] == app['expected_decision']
    print(f'Rules decisions using real extraction: {same}/{n} match expected decision '
          f'(expected labels were built from the mock extraction, so small differences are normal)')


if __name__ == '__main__':
    main()
