import os, tempfile, importlib.util, unittest
from pathlib import Path
# Use a temporary database so API tests never alter the demo database.
ROOT=Path(__file__).resolve().parents[1]
os.environ['ONBOARDIQ_TESTING']='1'
os.environ['ONBOARDIQ_DB']=str(Path(tempfile.gettempdir())/'onboardiq-test-suite.sqlite3')
spec=importlib.util.spec_from_file_location('local_app',ROOT/'local_app.py')
mod=importlib.util.module_from_spec(spec)
# Module uses ONBOARDIQ_DB to isolate tests from the demo database.
spec.loader.exec_module(mod)
from fastapi.testclient import TestClient
class LocalAppTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.client=TestClient(mod.app)
 def login(self,user='u1'):
  r=self.client.post('/api/v1/auth/login',json={'username':user,'password':'Passw0rd!'})
  self.assertEqual(r.status_code,200,r.text); return r.json()['access_token']
 def test_health_and_auth(self):
  self.assertEqual(self.client.get('/api/v1/health').json()['status'],'UP')
  self.assertEqual(self.client.post('/api/v1/auth/login',json={'username':'u1','password':'bad'}).status_code,401)
 def test_roles_and_seeded_applications(self):
  t=self.login('applicant1'); rows=self.client.get('/api/v1/applications',headers={'Authorization':'Bearer '+t}).json()
  self.assertTrue(rows); self.assertTrue(all(r['owner']=='applicant1' for r in rows))
  self.assertEqual(self.client.get('/api/v1/review/queue',headers={'Authorization':'Bearer '+t}).status_code,403)
 def test_rule_evaluation_and_checker_separation(self):
  officer=self.login('u1'); q=self.client.get('/api/v1/review/queue',headers={'Authorization':'Bearer '+officer}).json(); self.assertTrue(q)
  aid=q[0]['id']; ev=self.client.post(f'/api/v1/applications/{aid}/evaluate',headers={'Authorization':'Bearer '+officer}); self.assertEqual(ev.status_code,200,ev.text)
  rec=self.client.post(f'/api/v1/applications/{aid}/recommendation',headers={'Authorization':'Bearer '+officer},json={'recommendation':'APPROVE','comment':'Reviewed synthetic evidence'})
  self.assertEqual(rec.status_code,200,rec.text)
  same=self.client.post(f'/api/v1/applications/{aid}/checker-decision',headers={'Authorization':'Bearer '+officer},json={'decision':'APPROVE','comment':'Checker decision'})
  self.assertEqual(same.status_code,403)
  checker=self.login('u2'); ok=self.client.post(f'/api/v1/applications/{aid}/checker-decision',headers={'Authorization':'Bearer '+checker},json={'decision':'APPROVE','comment':'Independent review complete'})
  self.assertEqual(ok.status_code,200,ok.text); self.assertEqual(ok.json()['status'],'APPROVED')
 def test_no_full_aadhaar_upload(self):
  applicant=self.login('applicant1'); rows=self.client.get('/api/v1/applications',headers={'Authorization':'Bearer '+applicant}).json(); aid=rows[0]['id']
  import io
  r=self.client.post(f'/api/v1/applications/{aid}/documents?declared_doc_type=PAN_CARD',headers={'Authorization':'Bearer '+applicant},files={'file':('bad.txt',io.BytesIO(b'Aadhaar 123456789012'),'text/plain')})
  self.assertEqual(r.status_code,422)
if __name__=='__main__': unittest.main()
