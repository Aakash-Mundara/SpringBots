import csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RulesEngineTests(unittest.TestCase):
 def test_all_60_golden_applications(self):
  r=subprocess.run([sys.executable,str(ROOT/'scripts/run_batch.py'),'--verify-sample','--output',str(ROOT/'output/test_decisions.csv')],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
  self.assertIn('60/60 applications fully matched',r.stdout)
 def test_evaluation_batch_outputs_100_rows(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'decisions.csv'
   r=subprocess.run([sys.executable,str(ROOT/'scripts/run_batch.py'),'--applications',str(ROOT/'data/case_02_applications_eval_V1.0.csv'),'--documents',str(ROOT/'data/case_02_documents_eval_V1.0.csv'),'--extraction',str(ROOT/'data/case_02_extraction_mock_eval_V1.0.csv'),'--output',str(out)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   with out.open(newline='') as f: rows=list(csv.DictReader(f))
   self.assertEqual(len(rows),100)
   self.assertEqual(list(rows[0]),['application_id','decision','reason_codes','name_match_score','risk_category','rekyc_due_date'])
 def test_worked_example_four_similarity(self):
  with (ROOT/'output/test_decisions.csv').open(newline='') as f: rows={r['application_id']:r for r in csv.DictReader(f)}
  self.assertEqual(rows['A2000004']['name_match_score'],'0.7647')
  self.assertEqual(rows['A2000004']['reason_codes'],'NAME_MISMATCH_MINOR')
 def test_worked_examples_sanctions_and_pep(self):
  with (ROOT/'output/test_decisions.csv').open(newline='') as f: rows={r['application_id']:r for r in csv.DictReader(f)}
  self.assertEqual(rows['A2000006']['reason_codes'],'SANCTIONS_MATCH')
  self.assertEqual(rows['A2000007']['reason_codes'],'PEP_MATCH')
 def test_config_is_data_driven(self):
  cfg=json.loads((ROOT/'data/case_02_rules_config_V1.0.json').read_text())
  self.assertIn('name_match_threshold',cfg); self.assertIn('name_reject_below',cfg)
  self.assertIn('rekyc_years',cfg); self.assertIn('pan_pattern',cfg)
if __name__=='__main__': unittest.main(verbosity=2)
