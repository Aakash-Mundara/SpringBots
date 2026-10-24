#!/usr/bin/env python3
"""Portable local OnboardIQ app. Uses SQLite and local disk; no cloud or Docker required."""
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, Response
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, date, timedelta
import sqlite3, hashlib, hmac, base64, json, os, re, csv, io, secrets, sys
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; DB=Path(os.getenv('ONBOARDIQ_DB',str(ROOT/'local'/'onboardiq-local.sqlite3'))); UPLOADS=ROOT/'uploads'; WEB=ROOT/'web'
DB.parent.mkdir(exist_ok=True); UPLOADS.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from run_batch import RulesEngine, read_csv
sys.path.insert(0,str(ROOT))
import ocr_engine
from fastapi import Request
MAX_UPLOAD=10*1024*1024
MEDIA={'.txt':'text/plain','.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.bmp':'image/bmp','.tif':'image/tiff','.tiff':'image/tiff'}
engine=RulesEngine(DATA)
app=FastAPI(title='OnboardIQ Local MVP',version='1.0.0',description='Synthetic KYC onboarding and maker-checker workflow. Local-only.')
SECRET=os.getenv('JWT_SECRET','local-only-development-secret-change-me')
DISPLAY={'applicant1':'Demo Applicant One','applicant2':'Demo Applicant Two','u1':'Asha (KYC + Compliance)','officer2':'Rohan (KYC Officer)','u2':'Meera (Compliance Officer)'}
ROLES={'applicant1':['APPLICANT'],'applicant2':['APPLICANT'],'u1':['KYC_OFFICER','COMPLIANCE_OFFICER'],'officer2':['KYC_OFFICER'],'u2':['COMPLIANCE_OFFICER']}

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def hashpw(p,salt=None):
 salt=salt or secrets.token_hex(16); return salt+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),120000).hex()
def checkpw(p,h):
 try: s,v=h.split('$',1); return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),120000).hex(),v)
 except Exception:return False
def audit(c,actor,action,entity,entity_id,detail='{}'):
 c.execute('INSERT INTO audit_log(at,actor,action,entity,entity_id,detail) VALUES(?,?,?,?,?,?)',(datetime.utcnow().isoformat()+'Z',actor,action,entity,str(entity_id),detail))
def init():
 c=conn(); c.executescript('''CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL,roles TEXT NOT NULL,display_name TEXT NOT NULL); CREATE TABLE IF NOT EXISTS applications(id TEXT PRIMARY KEY,owner TEXT NOT NULL,application_date TEXT NOT NULL,full_name TEXT NOT NULL,dob TEXT NOT NULL,gender TEXT,pan_number TEXT NOT NULL,aadhaar_last4 TEXT NOT NULL,mobile TEXT,email TEXT,address TEXT,city TEXT,state TEXT,pincode TEXT,occupation_code TEXT,annual_income REAL,consent INTEGER DEFAULT 0,status TEXT DEFAULT 'DRAFT',submitted_at TEXT,decision_json TEXT,recommendation_json TEXT,checker_json TEXT,created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,application_id TEXT NOT NULL,file_name TEXT NOT NULL,declared_doc_type TEXT NOT NULL,path TEXT NOT NULL,extraction_json TEXT,uploaded_at TEXT NOT NULL,FOREIGN KEY(application_id) REFERENCES applications(id)); CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,actor TEXT,action TEXT,entity TEXT,entity_id TEXT,detail TEXT);''')
 cols={r[1] for r in c.execute('PRAGMA table_info(documents)')}
 for col in ('media_type','ocr_text_path','extraction_meta'):
  if col not in cols: c.execute(f'ALTER TABLE documents ADD COLUMN {col} TEXT')
 ucols={r[1] for r in c.execute('PRAGMA table_info(users)')}
 if 'created_at' not in ucols: c.execute('ALTER TABLE users ADD COLUMN created_at TEXT')
 for u,roles in ROLES.items():
  if not c.execute('SELECT 1 FROM users WHERE username=?',(u,)).fetchone(): c.execute('INSERT INTO users(username,password_hash,roles,display_name,created_at) VALUES(?,?,?,?,?)',(u,hashpw('Passw0rd!'),json.dumps(roles),DISPLAY.get(u,u),datetime.utcnow().isoformat()))
 if not c.execute('SELECT 1 FROM applications LIMIT 1').fetchone():
  apps=read_csv(DATA/'case_02_applications_sample_V1.0.csv')
  for r in apps:
   fields=['application_id','application_date','full_name','dob','gender','pan_number','aadhaar_last4','mobile','email','address','city','state','pincode','occupation_code','annual_income']
   vals=[r.get(x,'') for x in fields]; aid=vals[0]; owner='applicant1' if int(aid[-1])%2 else 'applicant2'
   c.execute('INSERT INTO applications(id,owner,application_date,full_name,dob,gender,pan_number,aadhaar_last4,mobile,email,address,city,state,pincode,occupation_code,annual_income,status,consent,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (aid,owner,*vals[1:], 'SUBMITTED',1,datetime.utcnow().isoformat()))
  # seed documents and their deterministic mock extraction fields
  docs=read_csv(DATA/'case_02_documents_sample_V1.0.csv'); ex={}
  texts={}
  try:
   for l in open(DATA/'case_02_document_text_sample_V1.0.jsonl',encoding='utf-8'): j=json.loads(l); texts[j['doc_id']]=j['text']
  except FileNotFoundError: pass
  for r in read_csv(DATA/'case_02_extraction_mock_sample_V1.0.csv'): ex.setdefault(r['doc_id'],{})[r['field_name']]={'value':r['value'],'confidence':float(r['confidence'] or 0)}
  for d in docs:
   docid=d['doc_id']; p=UPLOADS/(docid+'.txt'); p.write_text(texts.get(docid,'Synthetic seeded OCR fixture.\n'),encoding='utf-8')
   c.execute('INSERT OR IGNORE INTO documents(id,application_id,file_name,declared_doc_type,path,extraction_json,uploaded_at,media_type,ocr_text_path,extraction_meta) VALUES(?,?,?,?,?,?,?,?,?,?)',(docid,d['application_id'],d['file_name'],d['declared_doc_type'],str(p),json.dumps(ex.get(docid,{})),datetime.utcnow().isoformat(),'text/plain',str(p),json.dumps({'ocr_engine':'seed-fixture','note':'Seeded with supplied mock extraction (golden data)'})))
  audit(c,'system','SEED','database','sample','{"applications":60}')
 c.commit(); c.close()
init()

def token(user):
 payload={'sub':user['username'],'roles':json.loads(user['roles']),'exp':int((datetime.utcnow()+timedelta(hours=8)).timestamp())}
 b=base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).decode().rstrip('='); sig=base64.urlsafe_b64encode(hmac.new(SECRET.encode(),b.encode(),hashlib.sha256).digest()).decode().rstrip('='); return b+'.'+sig
def current(authorization: str|None=Header(default=None)):
 if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
 try:
  b,s=authorization[7:].split('.',1); expected=base64.urlsafe_b64encode(hmac.new(SECRET.encode(),b.encode(),hashlib.sha256).digest()).decode().rstrip('=')
  if not hmac.compare_digest(s,expected): raise ValueError()
  p=json.loads(base64.urlsafe_b64decode(b+'='*((4-len(b)%4)%4)))
  if p['exp']<datetime.utcnow().timestamp(): raise ValueError()
  return {'username':p['sub'],'roles':p['roles']}
 except Exception: raise HTTPException(401,'Invalid or expired token')
def require(*roles):
 def dep(u=Depends(current)):
  if not set(roles).intersection(u['roles']): raise HTTPException(403,'Insufficient role')
  return u
 return dep
def rowdict(r): return dict(r) if r else None
def get_app(c,aid):
 r=c.execute('SELECT * FROM applications WHERE id=?',(aid,)).fetchone()
 if not r: raise HTTPException(404,'Application not found')
 return dict(r)
def can_access(c,u,aid):
 a=get_app(c,aid)
 if 'APPLICANT' in u['roles'] and a['owner']!=u['username']: raise HTTPException(403,'Application belongs to another applicant')
 return a
class Login(BaseModel): username:str; password:str
class Register(BaseModel): username:str=Field(min_length=3,max_length=32,pattern=r'^[A-Za-z0-9_.-]+$'); password:str=Field(min_length=8,max_length=128); display_name:str=Field(min_length=2,max_length=100)
class ApplicationIn(BaseModel):
 full_name:str=Field(min_length=2,max_length=150); dob:date; gender:str=''; pan_number:str=Field(min_length=10,max_length=10); aadhaar_last4:str=Field(pattern=r'^\d{4}$'); mobile:str=''; email:str=''; address:str=''; city:str=''; state:str=''; pincode:str=Field(pattern=r'^\d{6}$'); occupation_code:str='SALARIED_PRIVATE'; annual_income:float=Field(ge=0); consent:bool
class ReviewIn(BaseModel): recommendation:str; comment:str=Field(min_length=3,max_length=2000)
class CheckerIn(BaseModel): decision:str; comment:str=Field(min_length=3,max_length=2000)
class CorrectionIn(BaseModel): doc_id:str; field_name:str; value:str; reason:str=Field(min_length=3,max_length=1000)
@app.get('/',response_class=HTMLResponse)
def home(): return (WEB/'index.html').read_text(encoding='utf-8')
@app.get('/api/v1/health')
def health(): return {'status':'UP','service':'onboardiq-local','storage':'local-disk','database':'sqlite','ocr_engine':ocr_engine.pick_engine()}
@app.post('/api/v1/auth/login')
def login(x:Login):
 c=conn(); u=c.execute('SELECT * FROM users WHERE username=?',(x.username,)).fetchone(); c.close()
 if not u or not checkpw(x.password,u['password_hash']): raise HTTPException(401,'Invalid credentials')
 return {'access_token':token(u),'token_type':'bearer','user':{'username':u['username'],'roles':json.loads(u['roles']),'display_name':u['display_name']}}
@app.post('/api/v1/auth/register')
def register(x:Register):
 if not re.search(r'[A-Za-z]',x.password) or not re.search(r'\d',x.password): raise HTTPException(422,'Password needs at least one letter and one digit')
 c=conn(); uname=x.username.lower()
 if c.execute('SELECT 1 FROM users WHERE lower(username)=?',(uname,)).fetchone(): c.close(); raise HTTPException(409,'Username already taken')
 c.execute('INSERT INTO users(username,password_hash,roles,display_name,created_at) VALUES(?,?,?,?,?)',(uname,hashpw(x.password),json.dumps(['APPLICANT']),x.display_name.strip(),datetime.utcnow().isoformat()))
 audit(c,uname,'REGISTER','user',uname); c.commit(); u=c.execute('SELECT * FROM users WHERE username=?',(uname,)).fetchone(); c.close()
 return {'access_token':token(u),'token_type':'bearer','user':{'username':uname,'roles':['APPLICANT'],'display_name':u['display_name']}}
@app.get('/api/v1/auth/me')
def me(u=Depends(current)): return u
@app.get('/api/v1/applications')
def applications(u=Depends(current),status:str|None=None):
 c=conn(); q='SELECT * FROM applications'; args=[]; wh=[]
 if 'APPLICANT' in u['roles']: wh.append('owner=?'); args.append(u['username'])
 if status: wh.append('status=?'); args.append(status)
 if wh:q+=' WHERE '+' AND '.join(wh)
 q+=' ORDER BY created_at DESC'; rows=[dict(r) for r in c.execute(q,args)]; c.close()
 for r in rows: r['decision']=json.loads(r.pop('decision_json') or 'null'); r['recommendation']=json.loads(r.pop('recommendation_json') or 'null'); r['checker']=json.loads(r.pop('checker_json') or 'null')
 return rows
@app.post('/api/v1/applications')
def create_application(x:ApplicationIn,u=Depends(require('APPLICANT'))):
 if not x.consent: raise HTTPException(422,'Consent is required')
 pan=x.pan_number.upper()
 if re.fullmatch(engine.cfg['pan_pattern'],pan) is None or pan[3]!=engine.cfg['pan_holder_type_char']: raise HTTPException(422,'PAN format or holder type is invalid')
 if len(re.sub(r'\D','',x.aadhaar_last4))!=4: raise HTTPException(422,'Store Aadhaar last four digits only')
 c=conn(); aid='A'+secrets.token_hex(4).upper()[:7]; data=x.model_dump(mode='json'); data['pan_number']=pan
 c.execute('INSERT INTO applications(id,owner,application_date,full_name,dob,gender,pan_number,aadhaar_last4,mobile,email,address,city,state,pincode,occupation_code,annual_income,consent,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(aid,u['username'],date.today().isoformat(),data['full_name'],data['dob'],data['gender'],pan,data['aadhaar_last4'],data['mobile'],data['email'],data['address'],data['city'],data['state'],data['pincode'],data['occupation_code'],data['annual_income'],1,'DRAFT',datetime.utcnow().isoformat())); audit(c,u['username'],'CREATE','application',aid); c.commit(); c.close(); return {'application_id':aid,'status':'DRAFT'}
@app.get('/api/v1/applications/{aid}')
def application_detail(aid:str,u=Depends(current)):
 c=conn(); a=can_access(c,u,aid); ds=[dict(r) for r in c.execute('SELECT id,file_name,declared_doc_type,extraction_json,uploaded_at,media_type,extraction_meta FROM documents WHERE application_id=?',(aid,))]; a['documents']=[{**d,'extraction':json.loads(d.pop('extraction_json') or '{}'),'meta':json.loads(d.pop('extraction_meta') or '{}')} for d in ds]; a['decision']=json.loads(a.pop('decision_json') or 'null');
 if 'APPLICANT' in u['roles']:
  for d in a['documents']:
   d['extraction']={k:{'value':v.get('value','')} for k,v in d['extraction'].items()}; d['meta']={k:d['meta'].get(k) for k in ('ocr_engine','duration_ms')}
  if a['decision']:
   a['decision']={k:v for k,v in a['decision'].items() if k in ('application_id','decision','reason_codes','risk_category','rekyc_due_date')}
 a['recommendation']=json.loads(a.pop('recommendation_json') or 'null'); a['checker']=json.loads(a.pop('checker_json') or 'null'); c.close(); return a
DOC_TYPES=('PAN_CARD','AADHAAR_CARD','ELECTRICITY_BILL','BANK_STATEMENT','DRIVING_LICENCE')
def _read_upload(file:UploadFile):
 ext=os.path.splitext((file.filename or '').lower())[1]
 if ext not in ocr_engine.SUPPORTED_EXT: raise HTTPException(415,'Supported files: PNG, JPG, WEBP, TIFF, BMP, PDF or .txt OCR text')
 raw=file.file.read(MAX_UPLOAD+1)
 if len(raw)>MAX_UPLOAD: raise HTTPException(413,'File limit is 10 MiB')
 if not raw: raise HTTPException(422,'Empty file')
 return ext,raw
def _run_extraction(raw,filename,declared):
 try: return ocr_engine.extract_document(raw,filename,declared)
 except ocr_engine.DocumentRejected as e: raise HTTPException(422,str(e))
 except RuntimeError as e: raise HTTPException(503,str(e))
@app.post('/api/v1/applications/{aid}/documents')
def upload_doc(aid:str,declared_doc_type:str,file:UploadFile=File(...),u=Depends(require('APPLICANT'))):
 if declared_doc_type not in DOC_TYPES: raise HTTPException(422,'Unknown declared document type')
 c=conn(); a=can_access(c,u,aid); c.close()
 ext,raw=_read_upload(file)
 res=_run_extraction(raw,file.filename,declared_doc_type)  # OCR + AI + Aadhaar guard before anything is persisted
 if a['status'] not in ('DRAFT','RESUBMISSION_REQUESTED'): raise HTTPException(409,'Documents can only be added to draft/resubmission applications')
 docid='D'+secrets.token_hex(6).upper(); path=UPLOADS/(docid+ext); path.write_bytes(raw); tpath=UPLOADS/(docid+'.ocr.txt'); tpath.write_text(res['text'],encoding='utf-8')
 meta=res['meta']; meta.pop('ai_raw',None)
 c=conn(); c.execute('INSERT INTO documents(id,application_id,file_name,declared_doc_type,path,extraction_json,uploaded_at,media_type,ocr_text_path,extraction_meta) VALUES(?,?,?,?,?,?,?,?,?,?)',(docid,aid,file.filename,declared_doc_type,str(path),json.dumps(res['fields']),datetime.utcnow().isoformat(),MEDIA.get(ext,'application/octet-stream'),str(tpath),json.dumps(meta)))
 audit(c,u['username'],'UPLOAD','document',docid,json.dumps({'application_id':aid,'file_name':file.filename,'ocr_engine':meta['ocr_engine'],'ai':meta['ai'].get('used'),'detected_type':res['fields']['doc_type']['value']})); c.commit(); c.close()
 return {'doc_id':docid,'extraction':{k:{'value':v['value']} for k,v in res['fields'].items()},'provider':meta['ocr_engine'],'ai_used':meta['ai'].get('used'),'detected_type':res['fields']['doc_type']['value']}
@app.post('/api/v1/ocr/scan')
def ocr_scan(file:UploadFile=File(...),u=Depends(require('APPLICANT'))):
 """Read a document without storing it (used to pre-fill the registration form)."""
 ext,raw=_read_upload(file); res=_run_extraction(raw,file.filename,None)
 return {'fields':{k:{'value':v['value'],'confidence':v['confidence']} for k,v in res['fields'].items()},'ocr_engine':res['meta']['ocr_engine'],'ai_used':res['meta']['ai'].get('used'),'duration_ms':res['meta']['duration_ms']}
@app.get('/api/v1/reference/occupations')
def occupations(u=Depends(current)): return [{'code':r['occupation_code'],'description':r['description']} for r in read_csv(DATA/'case_02_occupations_V1.0.csv')]
@app.get('/api/v1/ocr/status')
def ocr_status(u=Depends(current)): return ocr_engine.status()
@app.delete('/api/v1/applications/{aid}/documents/{docid}')
def delete_doc(aid:str,docid:str,u=Depends(require('APPLICANT'))):
 c=conn(); a=can_access(c,u,aid)
 if a['status'] not in ('DRAFT','RESUBMISSION_REQUESTED'): c.close(); raise HTTPException(409,'Documents are locked after submission')
 d=c.execute('SELECT * FROM documents WHERE id=? AND application_id=?',(docid,aid)).fetchone()
 if not d: c.close(); raise HTTPException(404,'Document not found')
 c.execute('DELETE FROM documents WHERE id=?',(docid,)); audit(c,u['username'],'DELETE_DOCUMENT','document',docid,json.dumps({'application_id':aid})); c.commit(); c.close()
 for pth in {d['path'],d['ocr_text_path']}:
  try:
   if pth: Path(pth).unlink()
  except OSError: pass
 return {'ok':True}
@app.post('/api/v1/documents/{docid}/reextract')
def reextract(docid:str,u=Depends(require('KYC_OFFICER'))):
 c=conn(); d=c.execute('SELECT * FROM documents WHERE id=?',(docid,)).fetchone()
 if not d: c.close(); raise HTTPException(404,'Document not found')
 raw=Path(d['path']).read_bytes(); name=d['file_name'] if os.path.splitext(d['file_name'].lower())[1] in ocr_engine.SUPPORTED_EXT else docid+'.txt'
 res=_run_extraction(raw,name,d['declared_doc_type']); old=json.loads(d['extraction_json'] or '{}')
 for k,v in old.items():
  if v.get('source')=='OFFICER_CORRECTION': res['fields'][k]=v  # keep human corrections
 meta=res['meta']; meta.pop('ai_raw',None); tpath=UPLOADS/(docid+'.ocr.txt'); tpath.write_text(res['text'],encoding='utf-8')
 c.execute('UPDATE documents SET extraction_json=?,extraction_meta=?,ocr_text_path=? WHERE id=?',(json.dumps(res['fields']),json.dumps(meta),str(tpath),docid))
 audit(c,u['username'],'REEXTRACT','document',docid,json.dumps({'application_id':d['application_id'],'ocr_engine':meta['ocr_engine'],'ai':meta['ai'].get('used')})); c.commit(); c.close()
 return {'doc_id':docid,'extraction':res['fields'],'meta':meta}
@app.get('/api/v1/documents/{docid}/ocr')
def document_ocr(docid:str,u=Depends(current)):
 c=conn(); d=c.execute('SELECT * FROM documents WHERE id=?',(docid,)).fetchone()
 if not d: c.close(); raise HTTPException(404,'Document not found')
 can_access(c,u,d['application_id']); c.close(); tp=Path(d['ocr_text_path'] or d['path'])
 text=tp.read_text(encoding='utf-8',errors='replace') if tp.exists() and tp.suffix=='.txt' else ''
 return {'doc_id':docid,'text':text,'media_type':d['media_type'] or 'text/plain','meta':json.loads(d['extraction_meta'] or '{}') if 'APPLICANT' not in u['roles'] else {}}
@app.post('/api/v1/applications/{aid}/submit')
def submit(aid:str,u=Depends(require('APPLICANT'))):
 c=conn(); a=can_access(c,u,aid)
 if not a['consent']: raise HTTPException(422,'Consent required')
 if a['status'] not in ('DRAFT','RESUBMISSION_REQUESTED'): raise HTTPException(409,'Application cannot be submitted from current status')
 if not c.execute('SELECT 1 FROM documents WHERE application_id=?',(aid,)).fetchone(): raise HTTPException(422,'Upload at least one document before submitting')
 now=datetime.utcnow().isoformat(); c.execute('UPDATE applications SET status=?,submitted_at=? WHERE id=?',('SUBMITTED',now,aid)); audit(c,u['username'],'SUBMIT','application',aid)
 # Deterministic rules run automatically on submission so every reviewer sees a result; KYC officers can re-run after corrections.
 result=evaluate_saved(c,a); c.execute('UPDATE applications SET decision_json=? WHERE id=?',(json.dumps(result),aid)); audit(c,'system','AUTO_EVALUATE','application',aid,json.dumps({'decision':result['decision'],'reason_codes':result['reason_codes']}))
 c.commit(); c.close(); return {'application_id':aid,'status':'SUBMITTED'}
def evaluate_saved(c,a):
 docs=[]
 for d in c.execute('SELECT * FROM documents WHERE application_id=?',(a['id'],)):
  ex=json.loads(d['extraction_json'] or '{}'); fields={k:v for k,v in ex.items()}; docs.append({'doc_id':d['id'],'declared_doc_type':d['declared_doc_type']})
  # adapt uploaded extraction fields into same shared deterministic engine interface
  for k,v in fields.items(): engine.extractions.setdefault(d['id'],{})[k]=v
 apprec={'application_id':a['id'],'application_date':a['application_date'],'full_name':a['full_name'],'dob':a['dob'],'pan_number':a['pan_number'],'aadhaar_last4':a['aadhaar_last4'],'pincode':a['pincode'],'occupation_code':a['occupation_code'],'annual_income':str(a['annual_income'] or 0)}
 return engine.evaluate(apprec,docs)
def backfill_evaluations():
 """Evaluate submitted cases that have no rules result yet (e.g. seeded sample data)."""
 c=conn(); n=0
 for r in c.execute("SELECT * FROM applications WHERE decision_json IS NULL AND status NOT IN ('DRAFT')").fetchall():
  a=dict(r); res=evaluate_saved(c,a); c.execute('UPDATE applications SET decision_json=? WHERE id=?',(json.dumps(res),a['id'])); n+=1
 if n: audit(c,'system','AUTO_EVALUATE','database','backfill',json.dumps({'applications':n}))
 c.commit(); c.close()
backfill_evaluations()
@app.post('/api/v1/applications/{aid}/evaluate')
def evaluate(aid:str,u=Depends(require('KYC_OFFICER','COMPLIANCE_OFFICER'))):
 c=conn(); a=get_app(c,aid)
 if a['status'] not in ('SUBMITTED','IN_REVIEW','RESUBMISSION_REQUESTED'): raise HTTPException(409,'Application is not ready for evaluation')
 result=evaluate_saved(c,a); c.execute('UPDATE applications SET status=?,decision_json=? WHERE id=?',('IN_REVIEW',json.dumps(result),aid)); audit(c,u['username'],'EVALUATE','application',aid,json.dumps({'decision':result['decision'],'reason_codes':result['reason_codes']})); c.commit(); c.close(); return result
@app.get('/api/v1/review/queue')
def review_queue(u=Depends(require('KYC_OFFICER','COMPLIANCE_OFFICER'))):
 c=conn(); rows=[dict(r) for r in c.execute("SELECT * FROM applications WHERE status IN ('SUBMITTED','IN_REVIEW','RESUBMISSION_REQUESTED') ORDER BY submitted_at")]; c.close()
 for a in rows:
  a['decision']=json.loads(a.pop('decision_json') or 'null'); a.pop('recommendation_json',None); a.pop('checker_json',None)
 return rows
@app.post('/api/v1/applications/{aid}/corrections')
def correction(aid:str,x:CorrectionIn,u=Depends(require('KYC_OFFICER'))):
 c=conn(); a=get_app(c,aid); d=c.execute('SELECT * FROM documents WHERE id=? AND application_id=?',(x.doc_id,aid)).fetchone()
 if not d: raise HTTPException(404,'Document not found')
 ex=json.loads(d['extraction_json'] or '{}'); old=ex.get(x.field_name,{}).get('value',''); ex[x.field_name]={'value':x.value,'confidence':1.0,'source':'OFFICER_CORRECTION'}
 c.execute('UPDATE documents SET extraction_json=? WHERE id=?',(json.dumps(ex),x.doc_id)); audit(c,u['username'],'FIELD_CORRECTION','document',x.doc_id,json.dumps({'field':x.field_name,'old':old,'new':x.value,'reason':x.reason})); c.commit(); c.close(); return {'ok':True,'old_value':old,'new_value':x.value}
@app.post('/api/v1/applications/{aid}/recommendation')
def recommendation(aid:str,x:ReviewIn,u=Depends(require('KYC_OFFICER'))):
 if x.recommendation not in ('APPROVE','REJECT','REQUEST_RESUBMISSION'): raise HTTPException(422,'Invalid recommendation')
 c=conn(); a=get_app(c,aid)
 if a['owner']==u['username']: raise HTTPException(403,'Maker cannot review own application')
 if a['status']!='IN_REVIEW' or not a['decision_json']: raise HTTPException(409,'Evaluate the application before making a recommendation')
 rec={'recommendation':x.recommendation,'comment':x.comment,'officer':u['username'],'at':datetime.utcnow().isoformat()}; c.execute('UPDATE applications SET recommendation_json=?,status=? WHERE id=?',(json.dumps(rec),'PENDING_CHECKER',aid)); audit(c,u['username'],'RECOMMEND','application',aid,json.dumps(rec)); c.commit(); c.close(); return rec
@app.get('/api/v1/checker/queue')
def checker_queue(u=Depends(require('COMPLIANCE_OFFICER'))):
 c=conn(); rows=[]
 for r in c.execute("SELECT * FROM applications WHERE status='PENDING_CHECKER'"):
  a=dict(r); a['recommendation']=json.loads(a.pop('recommendation_json') or 'null'); a.pop('decision_json',None); a.pop('checker_json',None); rows.append(a)
 c.close(); return rows
@app.post('/api/v1/applications/{aid}/checker-decision')
def checker_decision(aid:str,x:CheckerIn,u=Depends(require('COMPLIANCE_OFFICER'))):
 if x.decision not in ('APPROVE','REJECT','REQUEST_RESUBMISSION'): raise HTTPException(422,'Invalid checker decision')
 c=conn(); a=get_app(c,aid); rec=json.loads(a['recommendation_json'] or 'null')
 if a['status']!='PENDING_CHECKER' or not rec: raise HTTPException(409,'No maker recommendation to check')
 if rec['officer']==u['username']: raise HTTPException(403,'Maker and checker must be different users')
 chk={'decision':x.decision,'comment':x.comment,'checker':u['username'],'at':datetime.utcnow().isoformat()}; status={'APPROVE':'APPROVED','REJECT':'REJECTED','REQUEST_RESUBMISSION':'RESUBMISSION_REQUESTED'}[x.decision]
 c.execute('UPDATE applications SET checker_json=?,status=? WHERE id=?',(json.dumps(chk),status,aid)); audit(c,u['username'],'CHECKER_DECISION','application',aid,json.dumps(chk)); c.commit(); c.close(); return {'status':status,'checker':chk}
@app.get('/api/v1/dashboard')
def dashboard(u=Depends(require('KYC_OFFICER','COMPLIANCE_OFFICER'))):
 c=conn(); stats={r['status']:r['n'] for r in c.execute('SELECT status,count(*) n FROM applications GROUP BY status')}; decisions={}
 for r in c.execute('SELECT decision_json FROM applications WHERE decision_json IS NOT NULL'):
  d=json.loads(r[0]); decisions[d['decision']]=decisions.get(d['decision'],0)+1
 c.close(); return {'applications_by_status':stats,'evaluations_by_decision':decisions}
@app.get('/api/v1/audit')
def audit_list(limit:int=100,u=Depends(require('COMPLIANCE_OFFICER'))):
 c=conn(); rows=[dict(r) for r in c.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT ?', (min(max(limit,1),500),))]; c.close(); return rows
@app.get('/api/v1/audit/export.csv')
def audit_export(u=Depends(require('COMPLIANCE_OFFICER'))):
 c=conn(); rows=[dict(r) for r in c.execute('SELECT * FROM audit_log ORDER BY id')]; c.close(); out=io.StringIO(); w=csv.DictWriter(out,fieldnames=['id','at','actor','action','entity','entity_id','detail']); w.writeheader(); w.writerows(rows); return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=audit.csv'})
@app.get('/api/v1/admin/rules-config')
def rules_config(u=Depends(require('COMPLIANCE_OFFICER'))): return engine.cfg
@app.get('/api/v1/admin/reference-data')
def reference_data(u=Depends(require('COMPLIANCE_OFFICER'))):
 return {'occupations':read_csv(DATA/'case_02_occupations_V1.0.csv'),'sanctions_count':len(engine.sanctions),'pep_count':len(engine.peps),'existing_customers_count':len(engine.existing)}
@app.get('/api/v1/applications/{aid}/timeline')
def timeline(aid:str,u=Depends(current)):
 c=conn(); can_access(c,u,aid); rows=[dict(r) for r in c.execute("SELECT * FROM audit_log WHERE entity_id=? OR detail LIKE ? ORDER BY id",(aid,'%'+aid+'%'))]; c.close(); return rows
@app.get('/api/v1/documents/{docid}/content')
def document_content(docid:str,u=Depends(current)):
 c=conn(); d=c.execute('SELECT * FROM documents WHERE id=?',(docid,)).fetchone()
 if not d: c.close(); raise HTTPException(404,'Document not found')
 can_access(c,u,d['application_id']); path=Path(d['path']); c.close(); return FileResponse(path,media_type=d['media_type'] or 'text/plain',filename=d['file_name'],content_disposition_type='inline')
