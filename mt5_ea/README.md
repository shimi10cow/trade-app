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

## 現在の実装

- M15 SIMPLE STRATEGY 2026-09-26 を `m15_strategy.py` に実装
- Stochastic 14,5,3 / H1 20-75 regime / SMA200・480 slope / q75 / Retracement Gate / P1-P3
- +2R または 240h で Causal ZigZag trailing を開始。240h強制決済はしない
- Regimeが変わっても保有Trade Ledgerは維持
- GAS設定はバックグラウンド更新し、売買判定時はキャッシュを使用
- GAS保存はoutbox経由で売買判定経路を待たせない
- キャッシュが古すぎる場合は新規Entryを停止
- 実注文は引き続き `EA_DRY_RUN=true` が既定値


## DRY RUN常駐前に実装済みの保護

- EA環境確認日時がない・期限切れの場合は新規Entryをfail-closed
- TL推進/逆トレ方向とEntry方向を照合
- Pair単位Risk上限 + 全EAポジション総同時Risk上限
- MT5実ポジションはMagic Numberで識別し、ZigZag SLを利益方向にだけ更新
- 再起動時にMT5実ポジションとStateを再照合
- Strategy上成立したEntryは、実注文しない場合もVirtual TradeとしてExitまで追跡
- Stateがない初回起動では、閉じたM15履歴を時系列に再生してbootstrap
- GAS保存はSQLite outboxへ先に永続化し、失敗時は指数backoffで再送
- Poison messageが他の保存を永久停止させないよう、再送待ちの行を飛ばして処理
- DRY RUN起動スクリプトはpreflightとstrategy unit testを先に実行
