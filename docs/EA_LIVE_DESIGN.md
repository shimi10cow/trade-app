# 本番 EA の作り方（2026-10-24、作業の 2 番目「ロジックの作り直しと一致テスト」）

## 方針

- 研究のコードをそのまま本番に持っていくのではなく、研究と同じ計算をする「本番用の部品」を作り、同じ部品で過去データも流せるようにする
- 足が確定するたびに、銘柄ごとに直近のデータ（数千本）だけで計算し直す。研究の結果と同じトレードが出るかを EA ごとに確かめる（一致テスト）
- 一致テストは 2 つ
  1. 全期間で流した結果が、研究のトレード一覧（エントリーの時刻・向き・損切り・決済）と一致する
  2. 途中で区切ったデータ（その時点までしか知らない状態）で流しても、区切りより前のトレードが変わらない（未来のデータを使っていないことの確認）

## 確認済み：土台のダウ判定（dow_window_test.py）

- 途中から計算を始めても、M15・H1・H4 とも 100〜200 本で全期間の計算と完全に一致する（主要・仮のトレンドとも一致率 100%）
- 計算時間：直近 6,000 本で 0.1 秒（全期間 14.6 万本は 57 秒）→ 足が確定するたびに直近だけ計算すれば十分速い
- 長い MA（H4 の SMA1200＝日足 SMA200 相当）を使う EA があるので、H4 は 3,000 本（約 2 年）を使う

## 採用 19 本の元（研究のどのコード・設定か）

| キー | 元のスクリプト・設定 | 研究の結果ファイル | 後から足す条件 |
|---|---|---|---|
| R@EURUSD | regime_ea2.py `R2c` | results/regime2_R2c.csv | — |
| T2@EURUSD | regime_ea2.py `T1t` ＋横軸フィルター（§61） | results/regime2_T1t_axis.csv | H4 で 3 回目以降かつ調整の時間が直前の 0.7 倍未満なら入らない |
| T@US30 | regime_ea2.py `T1t` | ws_US30 regime2_T1t.csv | — |
| L@EURUSD | tl_ea.py `N2` | results/tl_N2.csv | — |
| L2@XAUUSD | tl_ea.py `N2` ＋抵抗フィルター（§58 付近） | ws_XAUUSD tl_N2_room1.csv | 近くの H4 抵抗まで 1ATR 未満なら入らない |
| A@EURUSD | retest_ea.py `N1` | results/retest_N1.csv | — |
| C@EURUSD | step2b_cl15.py `md4tri` | results/step2/cl15_md4tri.csv | — |
| C@USDJPY | 同上 | results/usdjpy/step2/cl15_md4tri.csv | 調整 24 本超・傾き 0.03 超 |
| J2@USDJPY | turn_tune2.py `h1major+hour0_10` | results/usdjpy/turn/jt2_h1major+hour0_10.csv | — |
| S@XAUUSD | st2.py `ma_prov_buy_mt3_h1a1` | ws_XAUUSD st2/S_ma_prov_buy_mt3_h1a1.csv | ロット半分 |
| S@BTCUSD | st2.py `ma_ma_buy_mt3_h1a2` | ws_BTCUSD st2/S_ma_ma_buy_mt3_h1a2.csv | 土日は入らない |
| Q@XAUUSD | q_ea.py（設定は確認中） | ws_XAUUSD q/ | ロット半分 |
| Q@XAGUSD | q_ea.py `0.8_24_any_dow_ref_h4` | ws_XAGUSD q/Q_0.8_24_any_dow_ref_h4.csv | — |
| Q@US30 | q_ea.py `1.0_24_ma_dow_ref_h1` | ws_US30 q/Q_1.0_24_ma_dow_ref_h1.csv | — |
| M@US30・M@US500 | idx_rsi2.py `200_10_ma5_st` | ws_US30／US500 rsi2/M_200_10_ma5_st.csv | — |
| DS@JP225 | ds_ea.py H1・左肩・2R | ws_JP225 ds/ | 押し 4ATR 以上 |
| DS@US500 | ds_ea.py H1・左肩・2R・買い | ws_US500 ds/ | 押し 4ATR 以上・買いだけ |
| DS@XAUUSD | ds_ea.py H1・右肩・H1 トレール・買い | ws_XAUUSD ds/DS_H1_shoulder_h1.csv | 押し 4ATR 以上・買いだけ |

- 本番の損切りはサーバー側に置くので、研究の「入った足の中の損切り」の補正（EA_ENTRY_BAR=1）を入れた結果を正解にする
- 暦の倍率（月初 3 日・ゴールドの金曜の買いは 1.5 倍）と DD10% で半分は、注文の段階（作業の 3 番目）で掛ける

## 進める順番

1. 部品の土台：データ（MT5 の足、サーバー時間のまま）、足の作り直し（M15→H1・H4・日足）、ダウ判定、ATR・MA
2. EA を 1 本ずつ移す → 一致テスト 1・2 を通す。新しい順（右肩 → RSI2 → Q → S → C・J2 → R・T・L・A）
3. 全部そろったら、19 本をまとめて過去に流し、組み合わせの成績（§106）が再現されるかを見る
