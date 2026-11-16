import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from lab import shard_names,decision_matrix
class Tests(unittest.TestCase):
 def test_nested_explain_deduplicates_shards(self):
  value={'queryPlanner':{'shards':[{'shardName':'shardA'},{'shardName':'shardB'}]},'execution':{'shardName':'shardA'}}
  self.assertEqual(shard_names(value),['shardA','shardB'])
 def test_missing_shard_names_not_fabricated(self):self.assertEqual(shard_names({'ok':1}),[])
 def test_whale_customer_is_not_hidden_by_hashing(self):
  m=decision_matrix();self.assertEqual(m['max_customer_frequency'],2000);self.assertEqual(m['rows'][1][1],1001)
if __name__=='__main__':unittest.main()
