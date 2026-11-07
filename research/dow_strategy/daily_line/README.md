# Daily trendline EA (research, 2026-11-07)

- `lines_v4.py`: daily trendlines (user definition). `build(..., early=True, h4c=None)` = the adopted version B: provisional at the
  first pullback swing, confirmed by the low/high update, steeper line redrawn from the previous point, deleted on a daily close
  beyond it or when the daily Dow turns.
- `zone.py`: entries near the line (0.5 ATR(D1)), H1 close beyond SMA20 with SMA20 sloping the trade way, then the M15 Dow turn;
  stop = farther of the M15 turn swing and the line (+0.5 ATR(H1)); exit trail from +1R (M15 adopted). Stages: I = final trades,
  J = exits by group, H = re-entry / zone width / H4-vs-daily deletion. Run: `python zone.py EURUSD I x x 60 d1del`.
- `lines_c.py`: version C (provisional points on H4 swings) - matched the user's lines worse than B, not used.
- `stdtable.py`: the standard results table; `port_now.py` / `old_rules.py`: portfolio inputs.
Paths inside point at the session's work folders (/home/user/trendlab/...); adjust when re-running.
