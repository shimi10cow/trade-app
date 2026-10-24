# 新しい EA を動かす手順（2026-10-24、まずデモ口座で）

ここまでで動く形になったもの：
- EA 本体：`mt5_ea/live/`（19 本の計算・注文・損切りの移動・決済・ロット計算・生存確認）
- 裏側：`gas/EA_Live.gs`（EA の設定・口座の状態・EA のトレード・ログ）
- アプリ：EA 設定タブ（`ea_live.js`）

追加（2026-10-24 その 2）：
- 予約エントリー（EA 設定タブの「予約エントリー」で通貨ペアの「＋予約」。M15／H1 のストキャスで EA 口座が自動で入る。マジックナンバー 780000）
- ホームに EA の保有中と予約中、履歴に「EA」タブ、分析の「EA」で EA ごとの成績とバックテストの比較・口座の推移
- 入れ替えに必要なこと：`gas/EA_Live.gs` を貼り直して新バージョンでデプロイ（表「Reservations」は自動で作られる）、PC は STOP → `git pull` → START

まだのもの：MT5 の取り込みの作り直し、表の整理（Trades への統合）、画面の改善。

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

1. https://github.com/shimi10cow/trade-app/archive/refs/heads/main.zip をダウンロードして展開（置き場所の例 `C:\TradeEA\`。OneDrive が同期するフォルダは避ける）
2. XM の MT5 を開き「ファイル」→「取引口座にログイン」で EA 用のデモ口座にログイン
3. `py -m pip install MetaTrader5 requests numpy pandas`（1 回だけ）
4. 展開したフォルダの `mt5_ea` で `CONFIGURE_LIVE_EA.bat`（GAS のアドレス・EA_KEY・口座番号。1 回だけ）
5. `CHECK_SYMBOLS.bat` で銘柄の対応を確認（注文は出ない）
6. `START_LIVE_EA_DEMO.bat` で起動
   - 別の口座のときは起動しない（口座番号の確認あり）
   - アプリで「稼働」にするまで注文は出さない
   - EA の記録とログは `C:\Users\（名前）\TradeEA_data`（プログラムを入れ替えても消えない）

### プログラムの更新
- ロジックを直して main に入れた後、必要な時だけ最新の ZIP を取って入れ替える（記録は別の場所なので消えない）
- PC で Claude Code（デスクトップアプリ、またはそのフォルダで `claude remote-control`）を使えば、「main から最新を取ってきて」と頼むだけで入れ替えられる

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
