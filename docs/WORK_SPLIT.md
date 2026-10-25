# 作業の住み分け（2026-10-25 夜 改定）

Claude Code を 2 か所で使う。**クラウドでできることはクラウド、この PC でしかできないことはデスクトップ**（ユーザーの方針 2026-10-25）。
同じファイルを両方で直さなければ、GitHub でぶつからない。引き継ぎは `docs/HANDOFF_DESKTOP_TO_CLOUD_20261025.md`。

| 呼び方 | どこ | 役目 |
|---|---|---|
| **クラウド** | claude.ai/code（クラウドの Claude Code） | アプリ・GAS・EA のプログラム・検証・研究・資料 |
| **デスクトップ** | 自宅 PC の Claude デスクトップアプリ（`C:\Users\81805\Documents\EA261024\trade-app`） | EA の起動・停止・確認、MT5、取り込みの実行、PC で動かす仕組み |

## デスクトップの担当（デスクトップだけが書き換える）

PC で EA や取り込みを動かす・止める・確かめるためのファイル。

- `mt5_ea/START_LIVE_EA_DEMO.bat` / `mt5_ea/START_LIVE_EA_REAL.bat` / `mt5_ea/STOP_LIVE_EA_DEMO.bat` / `mt5_ea/STOP_LIVE_EA_REAL.bat` / `mt5_ea/UPDATE_LIVE_EA.bat`
- `mt5_ea/IMPORT_MT5.bat` / `mt5_ea/IMPORT_MT5_REREAD90.bat` / `mt5_ea/run_import.ps1`（取り込みのボタン。中で動かす `mt5_ea/live/importer.py` はクラウド）
- `mt5_ea/CONFIGURE_LIVE_EA.bat` / `mt5_ea/CHECK_SYMBOLS.bat`
- `mt5_ea/start_live_ea.ps1`（見張り役）/ `mt5_ea/stop_live_ea.ps1` / `mt5_ea/update_live_ea.ps1` / `mt5_ea/configure_live_ea.ps1`
- `mt5_ea/setup_live_ea_desktop.ps1`（デスクトップのボタン作り）
- `mt5_ea/live/check_symbols.py`（銘柄の確認だけ。注文しない）
- `docs/EA_PC_OPERATION.md`（PC での動かし方）

## クラウドの担当（上以外ぜんぶ）

- アプリ：`index.html`・`app.js`・`ea_live.js`・`mt5_tab.js`・`ea.js`・`mt5_import.js`・`style.css`・`sw.js`・`manifest.json` ほか
- 裏側：`gas/`・`Code.gs`
- EA 本体：`mt5_ea/live/`（`check_symbols.py` 以外）。売買の判断・損切り・ロットを変えたら一致テスト
- 研究・検証：`research/`・`mt5_ea/live/tests/`
- 資料：`docs/`（`EA_PC_OPERATION.md` 以外）
- 古い EA のファイル（`mt5_ea/main.py` ほか）の整理

## 進め方

- **クラウド**
  - EA 本体を直して main に入れたら、ユーザー経由で PC に「最新を取ってきて」と頼む（PC が「新EA 更新」で入れ替える）
  - GAS はユーザーが修正がたまってからまとめてデプロイする。デプロイが要る変更は `docs/APP_REVIEW.md` の「次の GAS デプロイで入るもの」に書く
  - PC の担当ファイルを変えてほしい時は、内容をユーザー経由でデスクトップに渡す
- **デスクトップ**
  - 作業の前に `git pull`。上げるのは PC の担当ファイルだけ（main へ直接でよい）
  - ログで EA や取り込みのおかしな動きを見つけたら、自分では直さず、ログと状況をまとめてユーザーに渡す（クラウドで直す）
- **担当が決まっていない新しいファイル**：PC でしか動かせないものはデスクトップ、それ以外はクラウド。迷ったらユーザーに聞く
