import unittest
from copy import deepcopy
from process_map import link_measurement

class ConfirmedLinks(unittest.TestCase):
    def setUp(self):
        self.run={'date':'2025-08-16','chamber':'A','source_cell':'AD12','recipe':'PPPLS5K','diffuser_sn':'DIDDBB2002','susceptor_sn':'ASUBBBB2401'}
        self.base={'kind':'Spacing','date':'2025-08-13','chamber':'A','diffuser_sn':'DIDDBB2002','susceptor_sn':'ASUBBBB2401','id':'Spacing:B20','source_row':20,'reason':'재가공 Diffuser 교체'}
        self.after={**self.base,'id':'Spacing:B33','source_row':33,'reason':'CSD Bolt 조정 후 재측정 (Edge Gap -40mils)'}
    def test_confirmed_post_csd(self):
        result=link_measurement(self.run,[self.base,self.after],'Spacing')
        self.assertEqual(result[0]['id'],'Spacing:B33')
        self.assertIn('2025-08-13',result[1])
        flat=[{**r,'kind':'Diffuser Flatness','id':i,'source_row':row} for r,i,row in [(self.base,'Diff Flatness:C15',15),(self.after,'Diff Flatness:C24',24)]]
        self.assertEqual(link_measurement(self.run,flat,'Diffuser Flatness')[0]['id'],'Diff Flatness:C24')
    def test_other_year_run_does_not_use_approval(self):
        self.assertIsNone(link_measurement({**self.run,'date':'2026-08-16'},[self.base,self.after],'Spacing')[0])
    def test_2026_measurement_is_future(self):
        rows=[{**r,'date':'2026-08-13'} for r in [self.base,self.after]]
        self.assertIsNone(link_measurement(self.run,rows,'Spacing')[0])
    def test_2026_pair_is_not_approved(self):
        rows=[{**r,'date':'2026-08-13'} for r in [self.base,self.after]]
        self.assertIsNone(link_measurement({**self.run,'date':'2026-08-16'},rows,'Spacing')[0])
    def test_changed_run_or_state_does_not_use_approval(self):
        for field,value in [('chamber','B'),('source_cell','AM12'),('recipe','OTHER'),('diffuser_sn','WRONG'),('susceptor_sn','WRONG')]:
            with self.subTest(field=field):self.assertIsNone(link_measurement({**self.run,field:value},[self.base,self.after],'Spacing')[0])
        for field,value in [('reason','교체'),('source_row',999),('id','Spacing:B99')]:
            with self.subTest(field=field):self.assertIsNone(link_measurement(self.run,[self.base,{**self.after,field:value}],'Spacing')[0])
    def test_missing_duplicate_or_newer_candidate(self):
        self.assertIsNone(link_measurement(self.run,[self.base,{**self.base,'id':'other'}],'Spacing')[0])
        self.assertIsNone(link_measurement(self.run,[self.base,self.after,self.after],'Spacing')[0])
        wrong={**self.after,'date':'2025-08-15','diffuser_sn':'WRONG'}
        self.assertIsNone(link_measurement(self.run,[self.base,self.after,wrong],'Spacing')[0])
    def test_unambiguous_normal_match_preserved(self):
        self.assertEqual(link_measurement({**self.run,'source_cell':'other'},[self.base],'Spacing')[0]['id'],'Spacing:B20')
        self.assertIsNone(link_measurement(self.run,[self.base],'Spacing')[0])
        self.assertEqual(link_measurement(self.run,[self.after],'Spacing')[0]['id'],'Spacing:B33')

if __name__=='__main__':unittest.main()

