from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import joblib

class MLStrategy(Strategy):
    def init(self):
        self.model = joblib.load("model.pkl")
        self.data_features = self.I(
            lambda: self.model.predict(
                self.data.df[["SMA_10", "RSI", "Return"]].fillna(0)
            )
        )

    def next(self):
        if self.data_features[-1] == 1:
            if not self.position:
                self.buy()
        else:
            if self.position:
                self.position.close()

def run_backtest(df):
    bt = Backtest(df, MLStrategy, cash=10000, commission=0.001)
    stats = bt.run()
    return stats

if __name__ == "__main__":
    import data, features, model
    df = data.fetch_data()
    df = features.add_features(df)
    model.train_model(df)
    stats = run_backtest(df)
    print(stats)
