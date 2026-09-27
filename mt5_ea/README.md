# Hybrid EA runner

Windows + XM MT5 + Python 3.11 用。実注文は初期状態では停止しています。

## 最初にやること

PowerShellで `mt5_ea` フォルダへ移動して:

```powershell
pip install -r requirements.txt
.\start_dry_run.ps1
```

最初に `connection_test.py` が以下を検査します。

- XM MT5へのログイン
- EURUSD / USDJPY / EURJPY / AUDJPY / XAUUSD の現在価格
- 各通貨のM15確定足
- GAS `getEASettings`
- GAS `getPairs`

全部PASSした場合だけ `main.py` を起動します。

## 現在の安全状態

- `EA_DRY_RUN=true`
- 実注文は送信しない
- M15未確定バーは使わない
- Global停止 / Pair停止 / Signalのみ は注文不可
- GAS異常時は注文しない
- 注文候補は `order_check` まで
- Risk計算はBalance基準
- Risk上限を超える注文は拒否

## 重要

現在の `evaluate_m15()` は意図的に空です。
最新バックテストで使った Retracement Gate を含む正確なM15ロジック本体が保存ソースから完全には復元できていないため、近似ロジックで実注文候補を作らない安全設計です。

接続テストが通った後、正確なバックテストコードをこのstrategy adapterへ移植します。
