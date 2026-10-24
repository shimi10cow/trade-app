"""M5 base (2026-10-20): broker-time EURUSD M5 + causal Dow run on M5, cached.
Usage (build cache): DT_CACHE=<dir> DT_START=2005-01-01 python m5_base.py [SYM]"""
import os, sys, pickle, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load_m5  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
SYM = (sys.argv[1] if __name__ == '__main__' and len(sys.argv) > 1 else os.environ.get('M5_SYM', 'EURUSD'))
START = pd.Timestamp(os.environ.get('DT_START', '2005-01-01'))
CACHE = Path(os.environ.get('DT_CACHE', '/tmp')) / f'm5_{SYM}_{START.date()}.pkl'


def get():
    if CACHE.exists():
        return pickle.load(open(CACHE, 'rb'))
    m5 = load_m5(SYM); m5 = m5[m5.t >= START - pd.Timedelta(days=30)].reset_index(drop=True)
    t0 = time.time(); R5 = dow_trend.run(m5, 'M5')
    print(f'{SYM} M5 dow run {len(m5):,} bars in {time.time() - t0:.0f}s', flush=True)
    pickle.dump((m5, R5), open(CACHE, 'wb'))
    return m5, R5


if __name__ == '__main__':
    m5, R5 = get(); print(len(m5), len(R5['pivot_events']), len(R5['events']))
