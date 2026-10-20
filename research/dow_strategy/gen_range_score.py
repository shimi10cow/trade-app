"""Write results/h4_range_score.npy (range_detect.range_score, causal; no user labels needed)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import range_detect as RD  # noqa: E402
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('results') / 'h4_range_score.npy'
np.save(out, RD.range_score()); print(out)
