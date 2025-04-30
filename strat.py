import pandas as pd


def signals(data, short=15, long=40):  # 20 days for short term moving average, 50 for long term
    signals = data.copy()  # copy data to prevent modifying original directly
    signals["ShortMA"] = data["Price"].rolling(window=short).mean()
    signals["LongMA"] = data["Price"].rolling(window=long).mean()

    signals["Signal"] = 0  # initializes column 'Signal' to indicate Buy (1), Hold (0), or Sell (-1)
    signals.loc[signals.index[short:], "Signal"] = (
    (signals["ShortMA"].iloc[short:] > signals["LongMA"].iloc[short:]).astype(int)
    )  # Implementing Logic to derive appropriate signal

    signals["Position"] = signals["Signal"].diff()  # +1 = buy, 0 = hold, -1 = sell
    return signals

#applying stop-loss to make our strategy better
def stop_loss(signal_df, stop_loss_pct = 0.05):
    df = signal_df.copy()
    in_position = False
    entry_price = 0

    for i in range(1, len(df)):
        if df["Position"].iloc[i] == 1:
            in_position = True
            entry_price = (df["Price"].iloc[i]).item()

        elif in_position:
            current_price = (df["Price"].iloc[i]).item()
            drop = (entry_price - current_price) / entry_price

            if drop >= stop_loss_pct:
                in_position = False
                df.at[df.index[i], "Signal"] = 0
                df.at[df.index[i], "Position"] = -1

            elif df["Position"].iloc[i] == -1:
                in_position = False

    return df

