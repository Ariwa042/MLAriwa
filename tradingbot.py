from lumibot.strategies import Strategy
from datetime import datetime
from lumibot.brokers import Alpaca
from lumibot.traders import Trader
from lumibot.backtesting import YahooDataBacktesting
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment

API_KEY = "PK5RPNSN30CLYX4B4GOP"
API_SECRET = "YgCJTyR44sDi8ESITMlMHgpmQmVhc8aWvWnUP0xz"
ENDPOINT = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {"API_KEY": API_KEY, "API_SECRET": API_SECRET, "PAPER": True}

start_date = datetime(2023, 1, 1)
end_date = datetime(2024, 6, 31)


class MlTrader(Strategy):

    def initialize(self, symbol: str = "SPY", cash_risk: float = 0.01):
        self.symbol = symbol
        self.last_trade = None
        self.sleeptime = '24H'
        self.cash_risk = cash_risk
        self.api = REST(key_id=API_KEY,
                        secret_key=API_SECRET,
                        base_url=ENDPOINT)

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_risk / last_price, 0)

        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        start_time = today - Timedelta(days=3)
        return today.strftime("%Y-%m-%d"), start_time.strftime("%Y-%m-%d")

    def get_sentiment(self):
        today, start_time = self.get_dates()
        news = self.api.get_news(symbol=self.symbol,
                                 start=start_time,
                                 end=today)

        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability > 0.70:
                if self.last_trade != "buy":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price * 1.30,
                    stop_loss_price=last_price * 0.90,
                )
                self.submit_order(order)
                self.last_trade = "buy"

        elif sentiment == "negative" and probability > 0.70:
            if self.last_trade != "sell":
                self.buy_all()
            order = self.create_order(
                self.symbol,
                quantity,
                "sell",
                type="bracket",
                take_profit_price=last_price * .80,
                stop_loss_price=last_price * 1.05,
            )
            self.submit_order(order)
            self.last_trade = "sell"


broker = Alpaca(ALPACA_CREDS)
strategy = MlTrader(name='mlstrategy',
                    broker=broker,
                    parameters={
                        "symbol": "SPY",
                        "cash_risk": 0.01
                    })

strategy.backtest(YahooDataBacktesting,
                  start_date,
                  end_date,
                  parameters={
                      "symbol": "SPY",
                      "cash_risk": 0.01
                  })
