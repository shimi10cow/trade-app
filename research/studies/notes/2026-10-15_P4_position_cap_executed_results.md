# P4 x position cap research results — EURUSD 2003–2026

Unfiltered engine reruns, same other rules; no spread/slippage.

|Max P|Max simultaneous positions|Trades|Total R|PF|MaxDD R|
|---|---:|---:|---:|---:|---:|
|3|2|1398|+162.956|1.183|-58.180|
|4|2|1652|+79.523|1.073|-91.767|
|3|4|1662|+188.634|1.177|-81.816|
|4|4|2105|+130.876|1.095|-125.019|

P4 alone: 268 trades / -66.008R at cap2; 446 trades / -59.409R at cap4.

Retrospective selection from each rerun's executed trades, **NOT engine-internal filter-on reruns**:

|Max P|Cap|Filter A: n / R / PF|Filter B: n / R / PF|
|---|---:|---|---|
|3|2|483 / +95.071 / 1.319|388 / +110.242 / 1.472|
|4|2|543 / +82.280 / 1.240|442 / +95.955 / 1.350|
|3|4|561 / +101.324 / 1.287|447 / +127.664 / 1.468|
|4|4|671 / +105.161 / 1.245|534 / +125.191 / 1.377|

Filter A: confirmed H4 impulse >=70% previous, confirmed H1 impulse <75% previous. Filter B adds H1 SMA480 distance <12 ATR14. Causal 2-left/2-right confirmed fractal pivots; local recreation does not exactly match earlier 359/284 counts. Do not use as live EA rules until reconciled and validated. Research implementation in research/studies/ma_wave_filter_research.py. Production engine has NOT been changed.
