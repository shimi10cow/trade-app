# mt5_ea

今動いているのは `live/`（新しい EA・通知・取り込み・レポート）だけです。使い方は `docs/EA_LIVE_SETUP.md`。

| ボタン | 中身 |
|---|---|
| START_LIVE_EA_DEMO / REAL・STOP_… | EA（デモはこの時に「裁量の通知」の窓も開く。窓が開いている間は MT5 取り込みも 1 時間ごとに自動） |
| IMPORT_MT5 / IMPORT_MT5_REREAD90 | MT5 取り込みを今すぐ 1 回 |
| EA_REPORT | 週間レポート |
| PAIR_ENV | 通貨ペアの向き（週足込み、週末に） |
| ALERTS_START | 裁量の通知の窓だけ |
| UPDATE_LIVE_EA・CONFIGURE_LIVE_EA・GAS_DEPLOY(_SETUP)・CHECK_SYMBOLS | 更新・設定・GAS 反映・銘柄確認 |

古い EA（main.py ほか）は 2026-11-22 に削除しました（git の履歴に残っています）。
