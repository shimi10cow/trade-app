# 新しい EA を動かす手順（2026-10-24、まずデモ口座で）

ここまでで動く形になったもの：
- EA 本体：`mt5_ea/live/`（19 本の計算・注文・損切りの移動・決済・ロット計算・生存確認）
- 裏側：`gas/EA_Live.gs`（EA の設定・口座の状態・EA のトレード・ログ）
- アプリ：EA 設定タブ（`ea_live.js`）

まだのもの：予約エントリー、MT5 の取り込みの作り直し、表の整理（Trades への統合）、履歴の EA タブ、画面の改善。

## 1. 裏側（Google Apps Script）

1. スプレッドシート「トレードアプリ」の Apps Script を開く
2. 左のファイル一覧で「＋」→「スクリプト」→ 名前を `EA_Live` にして、`gas/EA_Live.gs` の中身を全部貼る
3. 今の `Code.gs` は置き換えず、2 か所だけ追記する（`ea` で始まる窓口を EA_Live に回すだけ）
   - doGet の `const action = e.parameter.action;` の下：
     `if (action && String(action).indexOf('ea') === 0 && typeof routeEALive_ === 'function') { const r = routeEALive_(action, e.parameter || {}); if (r) return ContentService.createTextOutput(JSON.stringify(r)).setMimeType(ContentService.MimeType.JSON); }`
   - doPost の `const action = body.action;` の下：
     `if (action && String(action).indexOf('ea') === 0 && typeof routeEALive_ === 'function') { const r = routeEALive_(action, body); if (r) return ContentService.createTextOutput(JSON.stringify(r)).setMimeType(ContentService.MimeType.JSON); }`
4. 左で `EA_Live` を開き、上の関数の選択で `eaSetupKeys` を選んで実行（初回は権限の許可） → 下の「実行ログ」に `EA_KEY = …` と `APP_KEY = …` が出る。2 つとも控える
5. 「デプロイ」→「デプロイを管理」→ 今のデプロイの鉛筆 →「バージョン：新バージョン」→「デプロイ」（アドレスは変わらない）
6. （任意）「トリガー」→ `eaWatchdog` を 1 時間ごと。PC が 2 時間止まったら Telegram に 1 回だけ通知（スクリプトのプロパティに TELEGRAM_BOT_TOKEN と TELEGRAM_CHAT_ID が必要）

## 2. 自宅 PC（EA 本体）

1. 最新のプログラムを入れる：https://github.com/shimi10cow/trade-app/archive/refs/heads/feature/env-recognition.zip を開いてダウンロード（約 150MB）→ 右クリック「すべて展開」→ できた `trade-app-feature-env-recognition` フォルダを使う（古い EA のフォルダとは別）
2. XM の MT5 を開き「ファイル」→「取引口座にログイン」で EA 用のデモ口座（極・円）にログイン
3. 展開したフォルダの `mt5_ea` を開き、アドレス欄に `powershell` と入れて Enter → `py -m pip install -r requirements.txt`（1 回だけ）
4. 同じ画面で `.\configure_live_ea.ps1` を実行して、GAS のアドレス・EA_KEY・デモ口座の番号・MT5 の場所を入れる（1 回だけ）
5. `START_LIVE_EA_DEMO.bat` をダブルクリックで起動
   - 別の口座のときは起動しない（口座番号の確認あり）
   - アプリで「稼働」にするまで注文は出さない（最初は「全体停止」）
   - 15 分足が確定するたびに計算し、ログは `mt5_ea/live/live.log`

## 3. アプリ

1. EA 設定タブを開くと合言葉を聞かれる → APP_KEY を入れる（この端末に保存、次から聞かれない）
2. デモ口座を選び、EA ごとに稼働モードと銘柄を確認 →「稼働」を押す
3. 数分以内に EA の PC がこの設定を受け取り、次の 15 分足から動く

※ アプリの新しい画面は、このブランチを main に取り込んだ後に公開される（GitHub Pages）。取り込みのタイミングは相談して決める。

## 動き方の決まり（設計どおり）

- 新しく入るのは、直前に確定した足でシグナルが出たものだけ（PC が止まっていた間の分には入らない）
- 損切りは必ず MT5 のサーバー側に置く。2R で決める右肩は利確もサーバー側
- ロット：普段のリスク × 暦の倍率（月初 3 日・ゴールドの金曜の買い 1.5 倍）× ロットの重み（ゴールドの S・Q は半分）× 0.5（最高値から 10% 以上減っている間）。最小ロットでも 1.5% を超えるなら入らない
- RSI(2) はサーバー時間 23:45〜23:55 にその時の値段を終値とみなして判定
- アプリの「シグナルのみ」は注文を出さず通知だけ。「停止」は計算もしない（保有中の分の損切り移動だけ続ける）
- EA ごとのマジックナンバーは 770000〜770018（registry.py の並び順）
