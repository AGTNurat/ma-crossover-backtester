import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from strat import signals, stop_loss

ticker = "TSLA"
data = yf.download(ticker, start="2019-01-01", end="2024-12-31")
data = data[["Close"]].rename(columns={"Close": "Price"})

start_date = data.index.min().strftime("%Y-%m-%d")
end_date = data.index.max().strftime("%Y-%m-%d")

#========Evaluation to find the best Short and Long MA================

def evaluate_strat(data, short, long):
    sig = signals(data, short, long)
    sig["Return"] = sig["Price"].pct_change()
    sig["Strategy Returns"] = sig["Return"] * sig["Signal"].shift(1)

    cum_return = (1 + sig["Strategy Returns"]).cumprod().iloc[-1]

    sharpe = (
    sig["Strategy Returns"].mean() / sig["Strategy Returns"].std()
    ) * (252 ** 0.5)

    return cum_return, sharpe

#testing short from 5 to 30 and long from 40 to 200
results = []
for short in range(5, 31, 5):
    for long in range(40, 201, 10):
        if short >= long:
            continue #short must be lesser than long

        cumulative, sharpe = evaluate_strat(data, short, long)
        results.append({
            "Short MA": short,
            "Long MA": long,
            "Cumulative Return": cumulative,
            "Sharpe Ratio": sharpe
        })

results_df = pd.DataFrame(results)
results_df = results_df.sort_values(by="Sharpe Ratio", ascending=False)

best_ma = results_df.iloc[0]
best_short = int(best_ma["Short MA"])
best_long = int(best_ma["Long MA"])



#===========stop-loss optimization to find the best stop loss %=====================

stop_results = []

short = 15
long = 40

for stop in [i / 100 for i in range (1, 11)]:
    sig = signals(data, short, long)
    sig = stop_loss(sig, stop_loss_pct=stop)

    sig["Return"] = sig["Price"].pct_change()
    sig["Strategy Returns"] = sig["Return"] * sig["Signal"].shift(1)

    cumulative = (1 + sig["Strategy Returns"]).cumprod().iloc[-1]

    sharpe = (
        sig["Strategy Returns"].mean() / sig["Strategy Returns"].std()
    ) * (252 ** 0.5)

    stop_results.append({
        "Stop Loss %": f"{int(stop * 100)}%",
        "Cumulative Return": cumulative,
        "Sharpe Ratio": sharpe
    })

stop_df = pd.DataFrame(stop_results)
stop_df["Stop Loss %"] = stop_df["Stop Loss %"].str.replace("%", "").astype(float)
stop_df = stop_df.sort_values(by="Sharpe Ratio", ascending=False)

best_stop = float(stop_df.iloc[0]["Stop Loss %"]) / 100


short = best_short
long = best_long
stop_loss_pct = best_stop

sig_data = signals(data, short=short, long=long)

sig_data = stop_loss(sig_data, stop_loss_pct=stop_loss_pct)

#==========Plotting Final Strategy price chart====================

plt.figure(figsize=(14, 7))
plt.plot(sig_data["Price"], label = "Price", alpha=0.5)
plt.plot(sig_data["ShortMA"], label = "Short MA", alpha=0.9)
plt.plot(sig_data["LongMA"], label = "Long MA", alpha=0.9)

#entry markers
plt.plot(sig_data[sig_data["Position"] == 1].index,
         sig_data.loc[sig_data["Position"] == 1, "Price"],
         "^", markersize=12, color="g", label="Buy Signal")

#exit markers
plt.plot(sig_data[sig_data["Position"] == -1].index,
         sig_data.loc[sig_data["Position"] == -1, "Price"],
         "v", markersize=12, color="r", label="Sell Signal")

plt.title(f"{ticker} - MA Crossover ({short}/{long}) with {int(stop_loss_pct * 100)}% Stop Loss")
plt.xlabel("Date")
plt.ylabel("Price ($)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("results/final_strategy_graph.png")
plt.show()


#================return calculations===================

sig_data["Return"] = sig_data["Price"].pct_change()

sig_data["Strategy Returns"] = sig_data["Return"] * sig_data["Signal"].shift(1)  #Returns only if we were holding the asset the day before

#cumulative returns calculation
sig_data["Cumulative Market"] = (1 + sig_data["Return"]).cumprod()
sig_data["Cumulative Strategy"] = (1 + sig_data["Strategy Returns"]).cumprod()

#plotting graph for cumulative returns for market buy and hold vs strategy return
plt.figure(figsize=(14, 7))
plt.plot(sig_data["Cumulative Market"], label = "Market Return (Buy & Hold)")
plt.plot(sig_data["Cumulative Strategy"], label = "Strategy Return (MA Crossover)")
plt.title(f"{ticker} - Cumulative Returns")
plt.xlabel("Date")
plt.ylabel("Cumulative Returns")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("results/cum_returns.png")
plt.show()

#Calculating Max Drawdown
sig_data["Rolling Max"] = sig_data["Cumulative Strategy"].cummax()
sig_data["Drawdown"] = sig_data["Cumulative Strategy"] / sig_data["Rolling Max"] - 1
max_drawdown = sig_data["Drawdown"].min()



#Calculation of Sharpe Ratio for our strategy
sharpe = (
    sig_data["Strategy Returns"].mean() / sig_data["Strategy Returns"].std()
) * (252**0.5)




#plotting sharpe ratio x stop loss % graph

plt.figure(figsize = (10, 6))
plt.plot(stop_df["Stop Loss %"], stop_df["Sharpe Ratio"], marker="o", linestyle="-", linewidth=2)
plt.title("Sharpe Ratio vs Stop Loss %")
plt.xlabel("Stop Loss (%)")
plt.ylabel("Sharpe Ratio")
plt.grid(True)
plt.xticks(stop_df["Stop Loss %"])

plt.tight_layout()
plt.savefig("results/sharpe_vs_stop_loss.png")
plt.show()

#adding trade metrics summary for more information

entry_signals = sig_data[sig_data["Position"] == 1]
exit_signals = sig_data[sig_data["Position"] == -1]

num_trades = len(entry_signals)

wins = 0
trade_returns = []

in_trade = False
entry_price = 0

for i in range (len(sig_data)):
    if sig_data["Position"].iloc[i] == 1:
        entry_price = sig_data["Price"].iloc[i].item()
        in_trade = True

    elif sig_data["Position"].iloc[i] == -1 and in_trade:
        exit_price = sig_data["Price"].iloc[i].item()
        ret = (exit_price - entry_price) / entry_price
        trade_returns.append(ret)
        if ret > 0:
            wins += 1
            in_trade = False

if len(trade_returns) > 0:
    win_rate = wins / len(trade_returns)
    avg_return = sum(trade_returns) / len(trade_returns)
else:
    win_rate = 0
    avg_return = 0




#================Plotting Drawdown====================================
plt.figure(figsize=(14, 5))
plt.plot(sig_data["Drawdown"], color = "red", label = "Drawdown")
plt.title("Strategy Drawdown over Time")
plt.xlabel("Date")
plt.ylabel("Drawdown (%)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("results/drawdown_plot.png")
plt.show()

total_return = (sig_data['Cumulative Strategy'].iloc[-1] - 1) * 100
buy_hold_return = (sig_data['Cumulative Market'].iloc[-1] - 1) * 100

#================Final Strategy Summary============================================
fig, ax = plt.subplots(figsize = (10, 6))
ax.axis("off")

text = f"""
Strategy Summary: {ticker}
Backtest Period: {start_date} -> {end_date}

Strategy: MA Crossover ({short}/{long}) with {int(stop_loss_pct * 100)}% Stop Loss

Final Results:
Sharpe Ratio: {sharpe:.2f}
Strategy Return: {total_return:.2f}%
Buy and Hold Return: {buy_hold_return:.2f}%
Max Drawdown: {max_drawdown:.2%}

Trade Metrics:
Total Trades: {num_trades}
Win Rate: {win_rate: .2%}
Avg. Return per Trade: {avg_return:.2%}
"""

ax.text(0, 1, text, fontsize = 13, va="top", ha = "left", family="monospace")

plt.tight_layout()
plt.savefig("results/final_summary_card.png")
plt.show()
