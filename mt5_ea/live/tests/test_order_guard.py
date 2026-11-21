"""The last check before every order (broker.MT5Broker.order_guard, 2026-11-21), with a fake MT5 on a JPY account.
Reproduces the 11/9 gold case (lots 158x too big) and other ways a lot size can go wrong; every bad order must be refused.
Usage: python -m mt5_ea.live.tests.test_order_guard"""
from types import SimpleNamespace as NS

from mt5_ea.live.broker import MT5Broker, OrderBlocked
from mt5_ea.live import sizing

USDJPY = 158.0


class FakeMT5:
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
    TRADE_ACTION_DEAL, ORDER_TIME_GTC, TRADE_RETCODE_DONE = 1, 0, 10009
    ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 1, 2

    def __init__(self, profit_in_usd=False, calc_none=False, equity=1_000_000, margin_free=1_000_000, margin_per_lot=None):
        self.profit_in_usd, self.calc_none, self.sent = profit_in_usd, calc_none, []
        self.acc = NS(login=1, server='x', balance=equity, equity=equity, currency='JPY', margin_free=margin_free, trade_mode=0)
        self.margin_per_lot = margin_per_lot or {}
        self.sym = {'GOLD#': NS(currency_profit='USD', trade_contract_size=100, trade_tick_size=0.01, trade_tick_value=0.01,   # tick value in USD (the bug)
                               volume_min=0.01, volume_step=0.01, volume_max=50, bid=4100.0, filling_mode=1, digits=2),
                    'EURUSD#': NS(currency_profit='USD', trade_contract_size=100000, trade_tick_size=0.00001, trade_tick_value=1.58,
                                  volume_min=0.01, volume_step=0.01, volume_max=50, bid=1.16, filling_mode=1, digits=5)}
        self.ticks = {'GOLD#': NS(bid=4100.0, ask=4100.3, time=0), 'EURUSD#': NS(bid=1.16, ask=1.16002, time=0), 'USDJPY#': NS(bid=USDJPY, ask=USDJPY, time=0)}

    def symbol_info(self, n): return self.sym.get(n)
    def symbol_info_tick(self, n): return self.ticks.get(n)
    def account_info(self): return self.acc
    def last_error(self): return (0, 'fake')

    def order_calc_profit(self, t, n, vol, p0, p1):
        if self.calc_none:
            return None
        i = self.sym[n]; usd = (p1 - p0) * (1 if t == self.ORDER_TYPE_BUY else -1) * vol * i.trade_contract_size
        return usd if self.profit_in_usd else usd * USDJPY

    def order_calc_margin(self, t, n, vol, p):
        return self.margin_per_lot.get(n, 0) * vol

    def order_check(self, req): return NS(retcode=0)

    def order_send(self, req):
        self.sent.append(req); return NS(retcode=self.TRADE_RETCODE_DONE, order=1, price=req['price'], volume=req['volume'])


def broker(m):
    b = MT5Broker.__new__(MT5Broker); b.mt5 = m; b.deviation = 20; b.name = lambda s: {'XAUUSD': 'GOLD#', 'EURUSD': 'EURUSD#'}[s]
    return b


def expect_block(label, fn):
    try:
        fn()
    except (OrderBlocked, RuntimeError) as ex:
        print(f'OK  止まった  {label}: {ex}'); return True
    print(f'NG  通ってしまった  {label}'); return False


def expect_pass(label, fn):
    try:
        r = fn(); print(f'OK  通った    {label}: {r}'); return True
    except Exception as ex:
        print(f'NG  止まってしまった  {label}: {ex}'); return False


def main():
    ok = []
    # 1. normal: gold 2% of 1,000,000 JPY with a $65 stop -> 0.01 lot (~10,270 JPY): passes
    m = FakeMT5(); b = broker(m); sp = b.spec('XAUUSD')
    lots, money, note = sizing.lots_for(sp, 1_000_000, 1_000_000, 0.02, 1, 1, 65.0)
    ok.append(expect_pass(f'ゴールド 正しいロット {lots} lot（想定 {money:,.0f} 円）', lambda: b.open('XAUUSD', 1, lots, 4100.3 - 65, None, 1, 'S', max_loss=money)))
    # 2. the 11/9 case: sizing believed 0.01 lot loses 65 JPY -> 1.51 lot with ~9,800 JPY meant
    ok.append(expect_block('11/9 と同じ：1.51 lot（想定 9,825 円）', lambda: b.open('XAUUSD', 1, 1.51, 4100.3 - 65, None, 1, 'S', max_loss=9825)))
    # 3. MT5's own profit calculation also wrong (USD, not JPY): the second (contract size x USDJPY) check disagrees 158x
    m3 = FakeMT5(profit_in_usd=True); b3 = broker(m3)
    ok.append(expect_block('MT5 の損益計算もドルで返る', lambda: b3.open('XAUUSD', 1, 1.51, 4100.3 - 65, None, 1, 'S', max_loss=9825)))
    # 4. MT5 cannot compute the profit: no lot size and no order
    m4 = FakeMT5(calc_none=True); b4 = broker(m4)
    ok.append(expect_block('損益計算ができない（ロット計算）', lambda: b4.spec('XAUUSD')))
    ok.append(expect_block('損益計算ができない（注文）', lambda: b4.open('XAUUSD', 1, 0.01, 4100.3 - 65, None, 1, 'S', max_loss=10000)))
    # 5. a big loss even though the settings asked for it (more than 5% of the equity)
    ok.append(expect_block('口座の 5% を超える損失（30 lot ユーロドル 50 pips）', lambda: b.open('EURUSD', 1, 3.0, 1.16002 - 0.0050, None, 1, 'T', max_loss=300000)))
    # 6. margin over half of the free margin
    m6 = FakeMT5(margin_per_lot={'EURUSD#': 400_000}); b6 = broker(m6)
    ok.append(expect_block('証拠金が余力の半分を超える', lambda: b6.open('EURUSD', 1, 2.0, 1.16002 - 0.0005, None, 1, 'T', max_loss=20000)))
    # 7. stop on the wrong side
    ok.append(expect_block('損切りが逆側', lambda: b.open('EURUSD', 1, 0.1, 1.17, None, 1, 'T', max_loss=10000)))
    # 7b. the trader's own reservation (equity_cap=None): a fixed 0.01 gold lot on a 10,000 JPY account is the trader's choice -> passes;
    #     but the 11/9 kind of mismatch is still refused for reservations
    mS = FakeMT5(equity=10_000, margin_free=10_000); bS = broker(mS)
    ok.append(expect_pass('予約（自分で決めた 0.01 lot、1 万円口座）', lambda: bS.open('XAUUSD', 1, 0.01, 4100.3 - 65, None, 1, 'R', max_loss=10270, equity_cap=None)))
    ok.append(expect_block('予約でも 2 通りの計算が合わなければ止める', lambda: broker(FakeMT5(profit_in_usd=True)).open('XAUUSD', 1, 0.01, 4100.3 - 65, None, 1, 'R', max_loss=10270, equity_cap=None)))
    ok.append(expect_block('EA の注文なら 1 万円口座で 0.01 lot ゴールドは止める（5%）', lambda: bS.open('XAUUSD', 1, 0.01, 4100.3 - 65, None, 1, 'S', max_loss=10270)))
    # 8. normal EURUSD: 1% risk, 30 pips -> passes, and the order really is sent
    sp2 = b.spec('EURUSD'); l2, mny, _ = sizing.lots_for(sp2, 1_000_000, 1_000_000, 0.01, 1, 1, 0.0030)
    ok.append(expect_pass(f'ユーロドル 正しいロット {l2} lot（想定 {mny:,.0f} 円）', lambda: b.open('EURUSD', 1, l2, 1.16002 - 0.0030, None, 1, 'T', max_loss=mny)))
    print(f'\n{sum(ok)}/{len(ok)} OK, sent orders: {len(m.sent)}')
    assert all(ok)


if __name__ == '__main__':
    main()
