# Hybrid EA runner

Windows PCでMT5ターミナルを起動した状態で動かすPython実行部です。

## 初回セットアップ

1. Python 3.11で仮想環境を作る
2. `pip install -r requirements.txt`
3. `.env.example` を参考に環境変数を設定
4. XMのMT5へログインしておく
5. 最初は必ず `EA_DRY_RUN=true`
6. `python main.py`

## 安全設計
- M15の未確定バーは使わない
- 初期状態はDRY RUN
- Global/Pair stopでは新規注文しない
- SignalはENTRY/SKIPともGASへ保存
- MT5/GAS異常時に実注文へフォールバックしない
- 実注文ONは接続・Signal・SL・lotを確認後に明示的に変更

## strategy
`evaluate_m15()` が唯一の戦略アダプタです。バックテスト済みのM15ロジックをここへ移植します。
