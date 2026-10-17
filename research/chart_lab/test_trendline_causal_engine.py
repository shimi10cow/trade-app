"""Smoke tests for causal line generation. Run: python -m unittest discover -s research/chart_lab -p 'test_*.py'"""
import unittest
import numpy as np
import pandas as pd
try:
    from .trendline_causal_engine import generate_lines, pivot_events, reanchor, asof_lines
except ImportError:
    from trendline_causal_engine import generate_lines, pivot_events, reanchor, asof_lines

class TestTrendlineCausality(unittest.TestCase):
    def setUp(self):
        x=np.arange(300);p=1.1+.01*np.sin(x*.3)+x*.00005
        self.df=pd.DataFrame(dict(t=pd.date_range('2020-01-01',periods=len(x),freq='15min'),
            o=p,h=p+.001,l=p-.001,c=p))
    def test_no_event_precedes_observation(self):
        for e in pivot_events(self.df,'M15'):
            self.assertGreaterEqual(e['available_idx'],e['idx'])
        lines=generate_lines(self.df,'M15')
        for e in lines:
            self.assertGreaterEqual(e['available_idx'],e['end_idx'])
        self.assertEqual([e['available_idx'] for e in lines],sorted(e['available_idx'] for e in lines))
    def test_future_bars_cannot_change_past_events(self):
        short=generate_lines(self.df.iloc[:180].copy(),'M15')
        full=generate_lines(self.df,'M15')
        earlier=[e for e in full if e['available_idx']<180]
        self.assertEqual(short,earlier)
    def test_reanchor_uses_outer_wick(self):
        p=np.array([10.,12.,9.,13.,11.])
        self.assertEqual(reanchor(0,4,p,'lo'),2)
    def test_asof(self):
        e=generate_lines(self.df,'M15')
        for k in (120,180,250):
            self.assertTrue(all(x['available_idx']<=k for x in asof_lines(e,k)))

if __name__=='__main__':unittest.main()
