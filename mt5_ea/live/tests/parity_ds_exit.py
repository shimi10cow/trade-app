"""Parity for the DS exit change (2026-11, RESEARCH_LOG §161): the new exit alone must equal the research 'E' run
(TRENDLAB/full/ds_stack.pkl), and with the cutover every trade / open position before it must equal the old (2R) run.
Usage: python -m mt5_ea.live.tests.parity_ds_exit"""
import os, pickle, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.eas import ds as DS  # noqa: E402
from mt5_ea.live.eas.nt import h4_shape  # noqa: E402
TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))
REF = pd.read_pickle(TL / 'full/ds_stack.pkl')
LAB = {'E': 'E H1で追う(+1.5R)・2つ目は1つ目が+1.5R後', 'A': 'A 2R利確・1つまで（今）'}
for sym in ('JP225', 'US500'):
    F = pickle.load(open(TL / f'live_frames_{sym}.pkl', 'rb')); sh = h4_shape(F.m15_all)
    gate = (lambda tr: tr[[sh(t, s)[0] < 2.5 for t, s in zip(tr.t, tr.side)]]) if sym == 'JP225' else (lambda tr: tr)
    key = lambda d: {(pd.Timestamp(t), int(s)) for t, s in zip(d.t, d.side)}
    new = gate(DS.run_adopted(F, sym, cutover=False)['trades']); ref = REF[(sym, LAB['E'])]
    print(sym, 'new exit vs research E:', len(new), len(ref), 'same', len(key(new) & key(ref)), f'R {new.R.sum() + 0:+.1f}')
    cut = pd.Timestamp('2021-01-01')
    mix = DS.run_adopted(F, sym, cutover=cut)['trades']; old = DS._adopted_once(F, DS.ADOPTED[sym], 'tp2', DS.setups(F, 'H1'), {e['t']: e['ln_h'] for e in DS.setups(F, 'H1')}, True)['trades']
    b = lambda d: d[pd.to_datetime(d.t) < cut]
    m1, o1 = b(mix), b(old)
    same_exit = (m1.sort_values('t').exit_t.values == o1.sort_values('t').exit_t.values).all() if len(m1) == len(o1) else False
    print(sym, 'cutover 2021-01: trades before it', len(m1), 'old run', len(o1), 'same entries', key(m1) == key(o1), 'same exits', same_exit)
