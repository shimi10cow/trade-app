# 作業の住み分け（2026-10-24〜）

Claude Code を 2 か所で使うので、ファイルごとに担当を決める。**担当外のファイルは書き換えない**。同じファイルを両方で直さなければ、GitHub でぶつからない。

| 呼び方 | どこ | 役目 |
|---|---|---|
| **クラウド** | claude.ai/code（クラウドの Claude Code） | ロジック・検証・研究、アプリと GAS の開発 |
| **PC** | 自宅 PC のデスクトップアプリ（`C:\Users\81805\Documents\EA261024\trade-app`） | EA の起動・停止・確認、PC で動かすための仕組み |

## PC の担当（PC だけが書き換える）

EA を PC で動かす・止める・確かめるためのファイル。

- `mt5_ea/START_LIVE_EA_DEMO.bat` / `mt5_ea/START_LIVE_EA_REAL.bat`
- `mt5_ea/STOP_LIVE_EA_DEMO.bat` / `mt5_ea/STOP_LIVE_EA_REAL.bat`
- `mt5_ea/UPDATE_LIVE_EA.bat`
- `mt5_ea/IMPORT_MT5.bat` / `mt5_ea/IMPORT_MT5_REREAD90.bat` / `mt5_ea/run_import.ps1`（取り込みのボタン。中で動かす `mt5_ea/live/importer.py` はクラウド）
- `mt5_ea/CONFIGURE_LIVE_EA.bat` / `mt5_ea/CHECK_SYMBOLS.bat`
- `mt5_ea/start_live_ea.ps1`（見張り役：自動の再起動・MT5 の立ち上げ直し・スリープ防止）/ `mt5_ea/stop_live_ea.ps1` / `mt5_ea/update_live_ea.ps1` / `mt5_ea/configure_live_ea.ps1`
- `mt5_ea/setup_live_ea_desktop.ps1`（デスクトップのボタン作り）
- `mt5_ea/live/check_symbols.py`（銘柄の確認だけ。注文しない）
- `docs/EA_PC_OPERATION.md`（PC での動かし方）

## クラウドの担当（クラウドだけが書き換える）

EA の中身と、それ以外のほぼ全部。

- `mt5_ea/live/` の中の上記以外すべて（`eas/`・`engine.py`・`core.py`・`sizing.py`・`registry.py`・`broker.py`・`runner.py`・`gas.py`・`env.py`・`main_live.py`・`tests/`）
- `research/`（検証・研究）
- `gas/`（裏側の Apps Script）
- アプリ：`index.html`・`app.js`・`ea_live.js`・`ea.js`・`style.css`・`sw.js`・`manifest.json` ほか
- `docs/EA_LIVE_SETUP.md`・`docs/EA_LIVE_DESIGN.md`・`docs/EA_SYSTEM_PLAN.md`
- データ（`*.zip`・`*.csv`・`xm_mt5_data/`）

## どちらも触らない

- 旧 EA のファイル（`mt5_ea/main.py`・`EA_START.bat`・`EA_STOP.bat`・`start_live.ps1`・`MT5_*` ほか、`mt5_ea/` 直下で上に出てこないもの）。消す・直すときはクラウドで決める
- このファイル（`docs/WORK_SPLIT.md`）は、持ち主（ユーザー）が決めたときだけ直す

## 進め方

- **PC**
  - 作業の前に `git pull` で main を最新にする。上げるのは PC の担当ファイルだけ（main へ直接でよい）
  - ロジックのおかしな動き（ログで見つけたもの）は自分で直さない。ログの該当部分と状況をまとめてユーザーに渡し、クラウドで直す
  - EA の入れ替えは「STOP → `git pull` → START」
- **クラウド**
  - PC の担当ファイルは直さない。変えてほしいときは、ユーザー経由で PC に頼む
  - 起動のしかたが変わる修正（環境変数の追加、`python -m` で起動するモジュール名の変更など）は、PC の担当ファイルの直しも要るので、何を変えたかをユーザーに伝える
- **担当が決まっていない新しいファイル**：EA の中身・検証ならクラウド、PC で動かすための仕組みなら PC。迷ったらユーザーに聞く
