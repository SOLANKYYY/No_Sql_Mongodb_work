import sys, unittest, json, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from data_source import normalize, read_export, load_dataset
class DataTests(unittest.TestCase):
    def row(self):return dict(id='1',source='a',target='b',type='x',timestamp='2025-01-02T01:30:00+05:30',indicator='ioc')
    def test_utc_day(self):
        d=normalize(self.row());self.assertEqual(d['day'],'2025-01-01');self.assertTrue(d['timestamp'].endswith('+00:00'))
    def test_missing_timezone(self):
        r=self.row();r['timestamp']='2025-01-01T00:00:00'
        with self.assertRaises(ValueError):normalize(r)
    def test_missing_required(self):
        r=self.row();r['source']=''
        with self.assertRaises(ValueError):normalize(r)
    def test_future(self):
        r=self.row();r['timestamp']='2099-01-01T00:00:00Z'
        with self.assertRaises(ValueError):normalize(r)
    def test_mapping(self):
        r=self.row();r['event_id']=r.pop('id')
        self.assertEqual(normalize(r,{'id':'event_id'})['id'],'1')
    def test_jsonl(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'threats.jsonl';p.write_text(json.dumps(self.row())+'\n')
            self.assertEqual(list(read_export(p)),[self.row()])
    def test_small_dataset_rejected_without_padding(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'threats.json').write_text(json.dumps([self.row()]))
            (p/'source.json').write_text(json.dumps({'source_name':'unit-test fixture','collected_at':'2025-02-01T00:00:00Z'}))
            with self.assertRaisesRegex(ValueError,'1,000 unique'):load_dataset(p)
    def test_conflicting_duplicates(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);a=self.row();b={**a,'source':'different'}
            (p/'threats.json').write_text(json.dumps([a,b]))
            (p/'source.json').write_text(json.dumps({'source_name':'fixture','collected_at':'2025-02-01T00:00:00Z'}))
            with self.assertRaisesRegex(ValueError,'Conflicting duplicate'):load_dataset(p)
if __name__=='__main__':unittest.main()
