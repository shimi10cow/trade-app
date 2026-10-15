# Experiment 03 — H4 RSI ablation

Baseline: e3e9ee62dfd1b74b6420c2bc9fa5100b17d44b2f

The shared runner already implements `--disable h4_rsi`. Do not modify engine H4 resampling, RSI state transitions, P numbering or other filters.

Run from the repository root with the 2003 M1 ZIP available under /mnt/data:

```bash
python research/shared_backtest_20261014/runner.py --pair EURUSD --h4 off --p p12 --disable none --tag exp03
python research/shared_backtest_20261014/runner.py --pair EURUSD --h4 off --p p12 --disable h4_rsi --tag exp03
python research/experiments/03_h4_rsi/compare.py
```

**Important:** P3 positions are simulated and only excluded after full execution. Differences between completed A/B trades do not identify all RSI-rejected signals, since position limits and subsequent state may differ. A precise rejected-signal attribution requires engine-level candidate logging before the RSI gate. Do not call unmatched completed trades 'RSI-rejected' without that instrumentation.
