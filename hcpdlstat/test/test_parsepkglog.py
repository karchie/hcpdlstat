import unittest
import hcpdlstat.parsepkglog as ppl

class TestParsePkgLog(unittest.TestCase):
    def get_state(self, logfile):
        s = ppl.init_state()
        with open(logfile) as f:
            ppl.handle_lines(f.readlines(), s)
        return s

    def test_g1(self):
        s = self.get_state('hcpdlstat/test/data/g1.log')
        self.assertEqual(1, s['g1'])
        self.assertEqual(1, s['g1_files'])
        self.assertEqual(0, s['g5'])
        self.assertEqual(0, s['g20'])
        self.assertEqual(1, s['files'])
        self.assertFalse(s['resources'])

    def test_g5(self):
        s = self.get_state('hcpdlstat/test/data/g5.log')
        self.assertEqual(0, s['g1'])
        self.assertEqual(1, s['g5'])
        self.assertEqual(0, s['g20'])
        self.assertEqual(3, s['g5_files'])
        self.assertEqual(15, s['files'])
        self.assertFalse(s['resources'])

    def test_g20(self):
        s = self.get_state('hcpdlstat/test/data/g20.log')
        self.assertEqual(0, s['g1'])
        self.assertEqual(0, s['g5'])
        self.assertEqual(1, s['g20'])
        self.assertEqual(11, s['g20_files'])
        self.assertEqual(220, s['files'])
        self.assertFalse(s['resources'])

    def test_group_avg(self):
        s = self.get_state('hcpdlstat/test/data/q1_group_avg.log')
        self.assertEqual(0, s['g1'])
        self.assertEqual(0, s['g5'])
        self.assertEqual(0, s['g20'])
        self.assertEqual(1, s['resources']['HCP_Q1']['Q1']['HCP_Q1-GroupAvgUnrelated20.zip'])

if __name__ == '__main__':
    unittest.main()
