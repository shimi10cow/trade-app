# EURUSD MA: causal filter-ON rerun, P1–P3, caps 2/3/4 (2026-10-15)

Method: Local reconstructed M15 engine, 583,458 EURUSD bars 2003–2026; entry-time filter gating before concurrent-position cap, with same stop/trailing, q75 and MA ABCD logic. No spread/slippage. Wave inputs use confirmed 2-left/2-right H1/H4 fractals with two fully closed right-hand candles; see research/studies/ma_wave_filter_research.py. Caveat: fractal feature reproduction does not exactly match earlier 359/284 study; research only, no production EA change.

Filter A: H4 latest/previous impulse >= 0.70 and H1 latest/previous impulse < 0.75.
Filter B: Filter A and H1 abs(close-SMA480)/ATR14 < 12.

|Filter|Cap|Trades|Total R|PF|Win %|Max DD R|2015+ trades|2015+ R|2015+ PF|2015+ DD R|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A|2|547|+92.703|1.269|35.83|-30.082|263|+56.028|1.364|-23.371|
|A|3|563|+99.324|1.280|35.88|-35.068|274|+58.932|1.364|-26.371|
|A|4|563|+99.324|1.280|35.88|-35.068|274|+58.932|1.364|-26.371|
|B|2|435|+119.872|1.452|38.16|-17.383|210|+69.712|1.595|-17.383|
|B|3|447|+127.664|1.468|38.26|-20.000|218|+72.788|1.591|-20.000|
|B|4|447|+127.664|1.468|38.26|-20.000|218|+72.788|1.591|-20.000|

Cap 3 and 4 identical for this tested filter configuration. Filter B cap 2 is lower DD; cap 3 adds +7.792R and -2.617R extra drawdown in full sample. The max DD is an additive trade R equity curve, not an account-level percentage or intra-bar portfolio equity DD. Chronological out-of-sample, cost, risk allocation and feature parity tests remain necessary.
