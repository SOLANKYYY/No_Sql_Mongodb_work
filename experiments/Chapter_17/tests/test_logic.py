import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from logic import chunks, normalized, recall, make_prompt
class LogicTests(unittest.TestCase):
    def test_chunk_overlap_and_tail(self):
        text=' '.join(map(str,range(201)));parts=chunks(text)
        self.assertEqual([len(p.split()) for p in parts],[100,100,41])
        self.assertEqual(parts[0].split()[-20:],parts[1].split()[:20])
        self.assertEqual(parts[-1].split()[-1],'200')
    def test_empty_text(self):self.assertEqual(chunks(''),[])
    def test_bad_overlap(self):
        with self.assertRaises(ValueError):chunks('x',100,100)
    def test_normalization(self):
        x=normalized(np.ones((2,384)))
        self.assertTrue(np.allclose(np.linalg.norm(x,axis=1),1))
    def test_invalid_embeddings(self):
        for a in [np.zeros((1,384)),np.ones((1,1536)),np.full((1,384),np.nan)]:
            with self.assertRaises(ValueError):normalized(a)
    def test_recall_ignores_missing_and_duplicates(self):self.assertEqual(recall([1,1,2,-1],[1,2,3,4]),.5)
    def test_memory_last_five(self):
        history=[{'question':'turn'+str(i),'answer':'answer'} for i in range(8)]
        prompt=make_prompt('new',[{'text':'evidence'}],history)
        self.assertNotIn('turn2',prompt)
        for i in range(3,8):self.assertIn('turn'+str(i),prompt)
if __name__=='__main__':unittest.main()
