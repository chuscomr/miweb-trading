class MarketData:
    def __init__(self, df):
        self.df = df.reset_index(drop=False)

    def iter_bars(self):
        total = len(self.df)
        for i in range(total):
            self._is_last = (i == total - 1)
            yield i, self.df.iloc[:i+1]

    def is_last_bar(self):
        return self._is_last
