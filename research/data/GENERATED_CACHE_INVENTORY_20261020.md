# ローソク足キャッシュ実生成結果 — 2026-10-20

**データ生成済み、GitHubへのバイナリデータ本体のpushは未完了。** この文書は実際にプロジェクト添付を読み、Pythonで集約した結果を記録する。元データと生成物はChatGPT作業環境の添付ファイルにある。GitHubコネクタから数十MB〜100MBのローカルバイナリを直接転送できないため、ここでは生成済みとアップロード済みを明確に区別する。

## 生成済みキャッシュ：全34データセット
| 銘柄・データ系列 | 入力期間 | M1 | M5 | M15 | H1 | H4 | D1 |
|---|---|---:|---:|---:|---:|---:|---:|
| EURUSD ForexTester M1 | 2003-05-06〜2026-10-12 | 8,602,190 | 1,741,198 | 583,458 | 146,274 | 37,805 | 7,329 |
| USDJPY ForexTester M1 | 2003-05-06〜2026-10-12 | 8,572,606 | 1,738,918 | 581,999 | 145,750 | 37,705 | 7,321 |
| EURUSD MT5 M5 | 2015-01-02〜2026-10-09 | — | 877,244 | 292,442 | 73,125 | 18,337 | 3,095 |
| USDJPY MT5 M5 | 2015-01-02〜2026-10-09 | — | 849,100 | 284,770 | 73,125 | 18,337 | 3,095 |
| JP225 MT5 M15 | 2015-01-02〜2026-10-09 | — | — | 235,225 | 61,521 | 16,344 | 3,043 |
| UK100 MT5 M15 | 2015-01-02〜2026-10-09 | — | — | 230,127 | 60,213 | 16,063 | 2,984 |
| US500 MT5 M15 | 2015-01-02〜2026-10-09 | — | — | 235,060 | 61,481 | 16,337 | 3,040 |

**期間不足**：EURUSD/USDJPYは2003-01-01〜2003-05-05のM1が不足。JP225/UK100/US500は2003〜2014年全期間の元データが不足。EURJPY/AUDJPY/XAUUSD/GBPUSD/AUDUSD/GBPJPYはこの作業環境にローソク足の元ファイルがなく、キャッシュ未生成。

## 生成ファイル構造
```
EA_candle_caches_20261020/
  MANIFEST.json
  EURUSD/
    m1/EURUSD2003.M1.zip, EURUSD_m1_{M5,M15,H1,H4,D1}.csv.gz
    mt5/EURUSD_mt5_{M5,M15,H1,H4,D1}.csv.gz
  USDJPY/
    m1/USDJPY2003.M1.zip, USDJPY_m1_{M5,M15,H1,H4,D1}.csv.gz
    mt5/USDJPY_mt5_{M5,M15,H1,H4,D1}.csv.gz
  JP225/mt5/JP225_mt5_{M15,H1,H4,D1}.csv.gz
  UK100/mt5/UK100_mt5_{M15,H1,H4,D1}.csv.gz
  US500/mt5/US500_mt5_{M15,H1,H4,D1}.csv.gz
```
M1は元ZIPをハッシュを変えずに保存。集約足は圧縮CSVで生成。MANIFESTにファイルごとのSHA256、期間、件数、元データSHA256を記録。

## スプレッド
- ForexTester M1: spread列なし。0pipsとみなさず、**欠損**。
- MT5: 元のspreadは**ブローカーのpoints単位**。M5/M15の元足にspreadを残す。集約足には `spread_last_points`、`spread_max_points`、`spread_mean_nonzero_points`、`spread_valid_count` を保存。
- `spread_mean_nonzero_points` は正の観測値だけを平均。0は不明値の可能性があるため平均に含めない。スプレッド0をゼロコストと仮定しない。
- pointsからpipsへの変換には銘柄固有のpoint sizeが必要。バックテストで使用する仮定スプレッド（EURUSD 1.0/1.2pip等）とは別管理。

## 注意
- M15 EURUSD 583,458本は以前の研究キャッシュの本数と一致。ただし**ローソク足価格・時刻の完全一致までは未検証**。
- ForexTester M1の元時刻はタイムゾーン未指定。MT5指数は明示UTC、MT5 FXは時刻帯未指定。異なるソースを自動結合しない。
- H4/D1は元データの時計で日付区切り。EAのH4環境判定に使う前にブローカー時刻との整合性を確認。
- 欠損期間の架空足は補完していない。最後の未確定足が含まれ得るので確定足のみでシグナル判定すること。
- 元データの取引所・配信元に応じた利用条件を確認すること。

## GitHubへの実データ移行
生成済みデータのZIPは会話添付から各銘柄ごとにダウンロードし、Git LFSを設定してpushする。大容量の元M1 ZIPも別添付。**GitHub上のこの文書はキャッシュ本体ではない。**

```bash
git lfs install
git lfs track "*.csv.gz" "*.M1.zip"
git add .gitattributes research/data/cache
git commit -m "data: import generated 2003-2026 multi-timeframe candle caches"
git push origin main
```
