#!/usr/bin/env python3
"""Deterministic OnboardIQ batch evaluator; reads all thresholds and reference lists from ./data."""
import argparse, csv, json, re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def norm_name(s, titles):
    s=(s or '').upper().replace('.', ' ').replace('-', ' ')
    s=re.sub(r'[^A-Z ]','',s)
    return ' '.join(sorted(t for t in re.sub(r'\s+',' ',s).strip().split() if t not in titles))
def similarity(a,b,titles):
    a,b=norm_name(a,titles),norm_name(b,titles)
    if not a and not b: return 1.0
    if not max(len(a),len(b)): return 1.0
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        cur=[i]
        for j,y in enumerate(b,1): cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=cur
    return 1-prev[-1]/max(len(a),len(b))
def dt(s):
    try: return date.fromisoformat((s or '').strip())
    except (ValueError, TypeError): return None
def age(dob, at): return at.year-dob.year-((at.month,at.day)<(dob.month,dob.day))
def truthy(v): return str(v or '').strip().lower() not in ('','false','0','no','null')

class RulesEngine:
 def __init__(self, data):
    self.data=Path(data); self.cfg=json.loads((self.data/'case_02_rules_config_V1.0.json').read_text(encoding='utf-8'))
    self.titles=set(self.cfg['name_title_tokens']); self.occ={r['occupation_code']:r['risk_level'] for r in read_csv(self.data/'case_02_occupations_V1.0.csv')}
    self.sanctions=read_csv(self.data/'case_02_sanctions_list_V1.0.csv'); self.peps=read_csv(self.data/'case_02_pep_list_V1.0.csv')
    self.existing=read_csv(self.data/'case_02_existing_customers_V1.0.csv')
    self.extractions={}
    for f in self.data.glob('case_02_extraction_mock_*.csv'):
      for r in read_csv(f): self.extractions.setdefault(r['doc_id'],{})[r['field_name']]={'value':r['value'].strip(),'confidence':float(r['confidence'] or 0)}
 def field(self, doc, key):
    x=doc.get(key,{}); return x.get('value',''),float(x.get('confidence',0))
 def usable(self,doc,key):
    v,c=self.field(doc,key); return (v.strip()!='' and c>=float(self.cfg['min_field_confidence']))
 def screen(self, entries, app, pep=False):
    best_match=None; best_possible=None
    for e in entries:
      scores=[similarity(app['full_name'],e.get('name',''),self.titles)]
      if e.get('alias','').strip(): scores.append(similarity(app['full_name'],e['alias'],self.titles))
      score=max(scores); edob=(e.get('dob') or '').strip(); same=(not edob or edob==app['dob'])
      hit={'entry':e,'score':score,'dob_match':same,'dob_comparison': 'NOT_PROVIDED' if not edob else ('MATCH' if same else 'DIFFERENT')}
      if score>=float(self.cfg['watchlist_match_threshold']) and same:
        if best_match is None or score>best_match['score']: best_match=hit
      elif score>=float(self.cfg['watchlist_possible_threshold']):
        if best_possible is None or score>best_possible['score']: best_possible=hit
    return ('MATCH',best_match) if best_match else (('POSSIBLE',best_possible) if best_possible and not pep else ('NONE',None))
 def evaluate(self, app, docs):
    # Extraction doc_type, not the user-declared type, selects documents.
    selected=[]
    for raw in sorted(docs,key=lambda x:x['doc_id']):
      fields=self.extractions.get(raw['doc_id'],{})
      typ=fields.get('doc_type',{}).get('value','OTHER') or 'OTHER'
      conf=float(fields.get('doc_type',{}).get('confidence',0))
      selected.append({'id':raw['doc_id'],'declared':raw['declared_doc_type'],'type':typ,'type_conf':conf,'fields':fields})
    pan=next((d for d in selected if d['type']=='PAN_CARD'),None)
    aad=next((d for d in selected if d['type']=='AADHAAR_CARD'),None)
    addr=next((d for d in selected if d['type'] in set(self.cfg['address_proof_types'])),None)
    reasons=[]; details={}
    def add(code, detail=None):
      reasons.append(code)
      if detail is not None: details[code]=detail
    # R1
    if not pan or not aad or not addr: add('DOCUMENT_MISSING')
    # R2
    mismatches=[d['id'] for d in selected if d['type'] != d['declared']]
    if mismatches: add('DOCUMENT_TYPE_MISMATCH', {'documents':mismatches})
    # R3 all docs low confidence and required fields on selected docs
    low=[d['id'] for d in selected if d['type_conf'] < float(self.cfg['min_field_confidence'])]
    required={'PAN_CARD':['name','dob','pan_number'],'AADHAAR_CARD':['name','dob','aadhaar_last4'],'ELECTRICITY_BILL':['pincode','document_date'],'BANK_STATEMENT':['pincode','document_date'],'DRIVING_LICENCE':['pincode','valid_until']}
    for d in [x for x in (pan,aad,addr) if x]:
      for k in required.get(d['type'],[]):
        if not self.usable(d['fields'],k): low.append(f"{d['id']}:{k}")
    if low: add('LOW_EXTRACTION_CONFIDENCE',{'items':low})
    # R4 age
    ad=dt(app.get('application_date')); dob=dt(app.get('dob'))
    if ad and dob and age(dob,ad)<int(self.cfg['min_age']): add('AGE_BELOW_18')
    # R5 declared PAN format and holder type
    panval=(app.get('pan_number') or '').strip().upper(); pattern=self.cfg['pan_pattern']
    if not re.fullmatch(pattern,panval) or len(panval)<4 or panval[3] != self.cfg['pan_holder_type_char']: add('PAN_INVALID')
    # R6
    if pan and self.usable(pan['fields'],'pan_number') and self.field(pan['fields'],'pan_number')[0].upper()!=panval: add('PAN_MISMATCH')
    # R7
    dobvals=[]
    for d in (pan,aad):
      if d and self.usable(d['fields'],'dob'):
        v=self.field(d['fields'],'dob')[0]
        if v != app.get('dob'): dobvals.append({'doc_id':d['id'],'value':v})
    if dobvals: add('DOB_MISMATCH',{'documents':dobvals})
    # R8
    if aad and self.usable(aad['fields'],'aadhaar_last4') and self.field(aad['fields'],'aadhaar_last4')[0] != app.get('aadhaar_last4'): add('AADHAAR_MISMATCH')
    # R9 / R11 name match based on usable PAN and Aadhaar names
    name_scores=[]
    for d in (pan,aad):
      if d and self.usable(d['fields'],'name'): name_scores.append((d['id'],similarity(app.get('full_name',''),self.field(d['fields'],'name')[0],self.titles)))
    score=min((s for _,s in name_scores),default=None)
    details['name_scores']=[{'doc_id':i,'similarity':round(s,4)} for i,s in name_scores]
    if score is not None and score<float(self.cfg['name_reject_below']): add('NAME_MISMATCH')
    # R10 sanctions match
    san_state,san_hit=self.screen(self.sanctions,app)
    if san_hit: details['sanctions']={'status':san_state,'list_id':san_hit['entry'].get('list_id'),'name':san_hit['entry'].get('name'),'similarity':round(san_hit['score'],4),'dob_comparison':san_hit['dob_comparison']}
    if san_state=='MATCH': add('SANCTIONS_MATCH',details['sanctions'])
    # R11
    if score is not None and float(self.cfg['name_reject_below'])<=score<float(self.cfg['name_match_threshold']): add('NAME_MISMATCH_MINOR')
    # R12
    if addr and addr['type']=='DRIVING_LICENCE' and self.usable(addr['fields'],'valid_until'):
      valid=dt(self.field(addr['fields'],'valid_until')[0])
      if ad and valid and valid<ad: add('DOCUMENT_EXPIRED',{'valid_until':valid.isoformat()})
    # R13
    if addr and addr['type'] in ('ELECTRICITY_BILL','BANK_STATEMENT') and self.usable(addr['fields'],'document_date'):
      dd=dt(self.field(addr['fields'],'document_date')[0])
      if ad and dd and (dd>ad or (ad-dd).days>int(self.cfg['address_proof_max_age_days'])): add('ADDRESS_PROOF_STALE',{'document_date':dd.isoformat()})
    # R14
    if addr and self.usable(addr['fields'],'pincode') and self.field(addr['fields'],'pincode')[0] != app.get('pincode'): add('ADDRESS_MISMATCH')
    # R15
    if san_state=='POSSIBLE': add('SANCTIONS_POSSIBLE_MATCH',details['sanctions'])
    # R16
    pep_state,pep_hit=self.screen(self.peps,app,pep=True)
    if pep_hit: details['pep']={'status':pep_state,'pep_id':pep_hit['entry'].get('pep_id'),'name':pep_hit['entry'].get('name'),'similarity':round(pep_hit['score'],4),'dob_comparison':pep_hit['dob_comparison']}
    if pep_state=='MATCH': add('PEP_MATCH',details['pep'])
    # R17
    duplicates=[x for x in self.existing if x.get('pan_number','').strip() and x['pan_number'].strip().upper()==panval]
    if duplicates: add('DUPLICATE_CUSTOMER',{'customer_id':duplicates[0].get('customer_id')})
    hard={'AGE_BELOW_18','PAN_INVALID','PAN_MISMATCH','DOB_MISMATCH','AADHAAR_MISMATCH','NAME_MISMATCH','SANCTIONS_MATCH'}
    review={'DOCUMENT_MISSING','DOCUMENT_TYPE_MISMATCH','LOW_EXTRACTION_CONFIDENCE','NAME_MISMATCH_MINOR','DOCUMENT_EXPIRED','ADDRESS_PROOF_STALE','ADDRESS_MISMATCH','SANCTIONS_POSSIBLE_MATCH','PEP_MATCH','DUPLICATE_CUSTOMER'}
    decision='REJECT' if hard.intersection(reasons) else ('REVIEW' if review.intersection(reasons) else 'APPROVE')
    risk=''; due=''
    if decision!='REJECT':
      occrisk=self.occ.get(app.get('occupation_code'),'LOW')
      if 'PEP_MATCH' in reasons or 'SANCTIONS_POSSIBLE_MATCH' in reasons or occrisk=='HIGH': risk='HIGH'
      elif occrisk=='MEDIUM' or float(app.get('annual_income') or 0)>=float(self.cfg['medium_risk_income']): risk='MEDIUM'
      else: risk='LOW'
      if ad: due=ad.replace(year=ad.year+int(self.cfg['rekyc_years'][risk])).isoformat()
      # Feb 29 maps to Feb 28
      if ad and risk and ad.month==2 and ad.day==29: due=date(ad.year+int(self.cfg['rekyc_years'][risk]),2,28).isoformat()
    return {'application_id':app['application_id'],'decision':decision,'reason_codes':'|'.join(reasons),'name_match_score':'' if score is None else f'{score:.4f}','risk_category':risk,'rekyc_due_date':due,'rule_details':details}

def main():
 p=argparse.ArgumentParser(); p.add_argument('--data',default=str(ROOT/'data')); p.add_argument('--applications',default=''); p.add_argument('--documents',default=''); p.add_argument('--extraction',default=''); p.add_argument('--output',default=str(ROOT/'output/decisions_output.csv')); p.add_argument('--verify-sample',action='store_true'); a=p.parse_args()
 data=Path(a.data); eng=RulesEngine(data)
 # Respect explicitly selected extraction CSV, otherwise merge supplied sample/eval mocks.
 if a.extraction:
  eng.extractions={}
  for r in read_csv(a.extraction): eng.extractions.setdefault(r['doc_id'],{})[r['field_name']]={'value':r['value'].strip(),'confidence':float(r['confidence'] or 0)}
 apps=read_csv(a.applications or data/'case_02_applications_sample_V1.0.csv')
 docs=read_csv(a.documents or data/'case_02_documents_sample_V1.0.csv'); byapp={}
 for d in docs: byapp.setdefault(d['application_id'],[]).append(d)
 out=[eng.evaluate(app,byapp.get(app['application_id'],[])) for app in apps]
 fields=['application_id','decision','reason_codes','name_match_score','risk_category','rekyc_due_date']
 write_csv(a.output,out,fields)
 print(f'Wrote {len(out)} decisions to {a.output}')
 if a.verify_sample:
  mism=[]
  for app,res in zip(apps,out):
   expected={'decision':app.get('expected_decision',''),'reason_codes':app.get('expected_reason_codes',''),'name_match_score':app.get('expected_name_match_score',''),'risk_category':app.get('expected_risk_category',''),'rekyc_due_date':app.get('expected_rekyc_due_date','')}
   for k,v in expected.items():
    actual=res[k]
    if k=='name_match_score' and v and actual and abs(float(v)-float(actual))<0.000051: continue
    if (v or '') != (actual or ''): mism.append((app['application_id'],k,v,actual))
  print(f'Sample verification: {len(apps)-len(set(x[0] for x in mism))}/{len(apps)} applications fully matched; {len(mism)} field mismatches')
  for x in mism[:30]: print('MISMATCH',*x,sep=' | ')
  if mism: raise SystemExit(1)
if __name__=='__main__': main()
