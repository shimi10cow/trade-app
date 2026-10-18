import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from env_recognition.ea_api import EnvRecognizer  # noqa
from env_recognition.data import load  # noqa


def test_state_at_uses_only_closed_bars_and_matches_truncated_run():
    frames = {tf: load(tf) for tf in ('D1', 'H4', 'H1')}
    full = EnvRecognizer(frames)
    ts = pd.Timestamp('2026-03-10 13:00')
    s_full = full.state_at(ts)
    # truncated data: only bars that had closed by ts
    cut = {tf: df[pd.to_datetime(df.t) + pd.Timedelta({'D1': '1D', 'H4': '4h', 'H1': '1h'}[tf]) <= ts]
           for tf, df in frames.items()}
    s_cut = EnvRecognizer(cut).state_at(ts)
    for tf in frames:
        a, b = s_full[tf], s_cut[tf]
        assert a['bar_time'] == b['bar_time']
        assert pd.Timestamp(a['bar_time']) + pd.Timedelta({'D1': '1D', 'H4': '4h', 'H1': '1h'}[tf]) <= ts
        for k in ('trend', 'protected', 'prov_trend', 'prov_protected'):
            assert a[k] == b[k]
        assert [(z['bottom'], z['top'], z['sources']) for z in a['zones']] == \
               [(z['bottom'], z['top'], z['sources']) for z in b['zones']]
        assert sorted((l['key'], round(l['value'], 8), l['broken'], l['cls']) for l in a['lines']) == \
               sorted((l['key'], round(l['value'], 8), l['broken'], l['cls']) for l in b['lines'])
