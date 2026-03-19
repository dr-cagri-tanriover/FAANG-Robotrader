
from pathlib import Path
from gradio_client import Client
import pandas as pd
from datetime import datetime, timedelta
import json
import csv

DATA_DIR = Path(__file__).parent / "data"

TRADER_ATTRIBUTES_FILE = DATA_DIR / "trader_attributes.json"


class TradingEngine:
    def __init__(self):

        self.ticker_map = {"AAPL": "APPLE", "AMZN": "AMAZON", "GOOG": "GOOGLE", "NFLX": "NETFLIX", "META": "META (a.k.a. Facebook)"}
        self.api_client = Client("ML-Owl/FAANG-Pulse-AI")

        with open(TRADER_ATTRIBUTES_FILE, 'r') as f:
            self.trader_attributes = json.load(f)

        self.backtesting_mode = False
        self.stock_tickers = ["AAPL", "AMZN", "GOOG", "NFLX", "META"]


    def get_stock_prices(self, tickers:list[str], date:str):
        tickers_list = self.ticker_map.keys()  # tickers for all supported stocks
        
        result = self.api_client.predict(
            stock_ticker_list=tickers,
            date_selected=date,
            api_name="/get_prices_on_date"
        )

        return result


    def get_sellable_shares(self, df_log:pd.DataFrame, ticker:str):
        # Returns the number of shares than can be sold for a stock in the portfolio.
        # Works as expected even when "ticker" is absent in df_log ! (i.e., returns 0)
        ticker_df = df_log[df_log["Ticker"] == ticker]  # sub-dataframe with transactions including "ticker" only.
        shares_bought = ticker_df[ticker_df["Action"] == "BUY"]["Shares"].sum()
        shares_sold = ticker_df[ticker_df["Action"] == "SELL"]["Shares"].sum()
        
        return shares_bought - shares_sold


    def run_trade_execution(self, stock_prices:dict):

        for eachInvestor in self.trader_attributes["investors"]:
            decision_threshold = self.trader_attributes["investors"][eachInvestor]["decision_threshold"]
            trade_log_file = self.trader_attributes["investors"][eachInvestor]["trade_log_file"]
            trade_log_file_path = DATA_DIR / trade_log_file
            df_log = pd.read_csv(trade_log_file_path)

            for eachStock in stock_prices:
                # Get trend prediction from AI using FAANG Pulse AI API
                predicted_trend, _ = self.api_client.predict(
                    stocks_dropdown=self.ticker_map[eachStock],
                    calendar_item=stock_prices[eachStock]["Date"], # using the actual date reported by the API for which there is price data!
                    risk_slider=decision_threshold,
                    api_name="/run_trend_prediction"
                )

                strategy_fn = self.get_trading_strategy(eachInvestor)  # get the relevant function to call for the investor
                df_log = strategy_fn(
                    investor_name=eachInvestor,
                    ticker=eachStock,
                    stock_prices=stock_prices,
                    date=stock_prices[eachStock]["Date"],
                    predicted_trend=predicted_trend,
                    df_log=df_log
                    )

                df_log.to_csv(trade_log_file_path, index=False)  # replace CSV with full updated log for this investor


    def get_trading_strategy(self, investor_name:str):
        # Returns the investment strategy function to caller to use for this investor
        investor_strategy_map = {
            "Safe_Sam": self.safe_strategy,
            "Optimal_Owen": self.optimal_strategy,
            "Brave_Beth": self.brave_strategy
        }

        return investor_strategy_map[investor_name]


    def build_new_transaction_row(self, new_row:dict, df_log:pd.DataFrame, investor_name:str, max_shares_to_buy:int, max_shares_to_sell:int):
        """
        Builds a new transaction row for the transaction log based on common trading logic.
        """

        # Readback pre-populated values from new_row
        predicted_trend = new_row["Direction"]
        price_per_share = new_row["Price"]  # We use (Adjusted) Close price to calculate the cost of the trade
        ticker = new_row["Ticker"]

        if df_log.empty:
            # First ever trade for this investor
            available_cash = self.trader_attributes["investors"][investor_name]["cash_allocated"]  # Initial budget
        else:
            # There are trade transactions in the log file already.
            available_cash = df_log.iloc[-1]["Cash After Trade"]  # Last entry keeps track of the available cash.


        if predicted_trend == "TREND_UP":
            # Opportunity to BUY
            shares_to_buy = min(max_shares_to_buy, available_cash // price_per_share)
            if shares_to_buy > 0:
                new_row["Action"] = "BUY"
                new_row["Shares"] = shares_to_buy
                new_row["Cash Before Trade"] = available_cash
                new_row["Cash After Trade"] = available_cash - (shares_to_buy * price_per_share)

        if predicted_trend == "TREND_DOWN":
            sellable_shares = self.get_sellable_shares(df_log, ticker)
            shares_to_sell = min(max_shares_to_sell, sellable_shares)
            if shares_to_sell > 0:
                new_row["Action"] = "SELL"
                new_row["Shares"] = shares_to_sell
                new_row["Cash Before Trade"] = available_cash
                new_row["Cash After Trade"] = available_cash + (shares_to_sell * price_per_share)

        if new_row["Action"] == "NONE":
            # If Action is still invalid at this point, a HOLD transaction is the only valid action.
            # Log this as a HOLD transaction. Since there is no cash to buy.
            new_row["Action"] = "HOLD"
            new_row["Shares"] = 0
            new_row["Cash Before Trade"] = available_cash
            new_row["Cash After Trade"] = available_cash

        return new_row



    def safe_strategy(self, investor_name:str, ticker: str, stock_prices:dict, date: str, predicted_trend:str, df_log:pd.DataFrame):
        """
        Safe Sam strategy:
        - If date is the same as the last trade date in log, do nothing and exit the function. (this happens when markets are closed!)
        - If the predicted trend is TREND_UP, BUY 50 shares.
        - else if the predicted trend is TREND_DOWN SELL 100 shares
        - else (if NO_TREND) HOLD the position.

        The BUY actions will be executed ONLY if there is enough cash available. If not, BUY as much as possible and then HOLD the position.
        """

        # If date is the same as the last trade date in log AND the ticker is the same as the last trade ticker,
        # then do nothing and exit the function. (this happens when markets are closed!)
        if date in df_log[df_log['Ticker']==ticker]['Date'].values:
            return df_log

        max_shares_to_buy, max_shares_to_sell = 50, 100

        price_per_share = stock_prices[ticker]["Close"]  # We use (Adjusted) Close price to calculate the cost of the trade

        # Initialize new row for the transaction log.
        # Following columns will be added to df_log regardless of the action taken.
        new_row = {
            "Date": date,
            "Ticker": ticker,
            "Price": price_per_share,
            "Direction": predicted_trend,
            "Action": "NONE"  # initialized to an invalid entry to simplify code below.
        }

        # Following is the common trading logic for all investors.
        new_row = self.build_new_transaction_row(new_row,df_log, investor_name, max_shares_to_buy, max_shares_to_sell)

        # New transaction log created.
        df_log.loc[len(df_log)] = new_row  # Added to the end of df_log dataframe
        
        return df_log


    def optimal_strategy(self, investor_name:str, ticker: str, stock_prices:dict, date: str, predicted_trend:str, df_log:pd.DataFrame):
        """
        Optimal Owen strategy:
        - If date is the same as the last trade date in log, do nothing and exit the function. (this happens when markets are closed!)
        - If the predicted trend is TREND_UP BUY 20 shares.
        - else if the predicted trend is TREND_DOWN SELL 20 shares
        - else (if NO_TREND) HOLD the position.

        The BUY actions will be executed ONLY if there is enough cash available. If not, BUY as much as possible and then HOLD the position.
        """

        # If date is the same as the last trade date in log AND the ticker is the same as the last trade ticker,
        # then do nothing and exit the function. (this happens when markets are closed!)
        if date in df_log[df_log['Ticker']==ticker]['Date'].values:
            return df_log

        max_shares_to_buy, max_shares_to_sell = 20, 20
        price_per_share = stock_prices[ticker]["Close"]  # We use (Adjusted) Close price to calculate the cost of the trade

        # Initialize new row for the transaction log.
        # Following columns will be added to df_log regardless of the action taken.
        new_row = {
            "Date": date,
            "Ticker": ticker,
            "Price": price_per_share,
            "Direction": predicted_trend,
            "Action": "NONE"  # initialized to an invalid entry to simplify code below.
        }

        # Following is the common trading logic for all investors.
        new_row = self.build_new_transaction_row(new_row,df_log, investor_name, max_shares_to_buy, max_shares_to_sell)

        # New transaction log created.
        df_log.loc[len(df_log)] = new_row  # Added to the end of df_log dataframe
        
        return df_log



    def brave_strategy(self, investor_name:str, ticker: str, stock_prices:dict, date: str, predicted_trend:str, df_log:pd.DataFrame):
        """
        Brave Beth strategy:
        - If date is the same as the last trade date in log, do nothing and exit the function. (this happens when markets are closed!)
        - If the predicted trend is TREND_UP BUY 10 shares.
        - else if the predicted trend is TREND_DOWN SELL 10 shares.
        - else (if NO_TREND) HOLD the position.

        The BUY actions will be executed ONLY if there is enough cash available. If not, BUY as much as possible and then HOLD the position.
        """   
        # If date is the same as the last trade date in log AND the ticker is the same as the last trade ticker,
        # then do nothing and exit the function. (this happens when markets are closed!)
        if date in df_log[df_log['Ticker']==ticker]['Date'].values:
            return df_log

        max_shares_to_buy, max_shares_to_sell = 10, 10

        price_per_share = stock_prices[ticker]["Close"]  # We use (Adjusted) Close price to calculate the cost of the trade

        # Initialize new row for the transaction log.
        # Following columns will be added to df_log regardless of the action taken.
        new_row = {
            "Date": date,
            "Ticker": ticker,
            "Price": price_per_share,
            "Direction": predicted_trend,
            "Action": "NONE"  # initialized to an invalid entry to simplify code below.
        }

        # Following is the common trading logic for all investors.
        new_row = self.build_new_transaction_row(new_row,df_log, investor_name, max_shares_to_buy, max_shares_to_sell)

        # New transaction log created.
        df_log.loc[len(df_log)] = new_row  # Added to the end of df_log dataframe
        
        return df_log


def live_trading():
    trading_engine = TradingEngine()
    tickers_list = list(trading_engine.ticker_map.keys())  # price data for all available stock tickers requested
    date_selected = datetime.now().strftime("%Y-%m-%d")  # get today's date at each call

    # API call to get FAANG stock OHLCV data for today
    stock_prices = trading_engine.get_stock_prices(tickers_list, date_selected)
 
    # Run trade execution logic using stock_prices
    trading_engine.run_trade_execution(stock_prices)


def test_trading():
    
    trading_engine = TradingEngine()

    tickers_list = list(trading_engine.ticker_map.keys())  # price data for all available stock tickers requested
    date_selected = trading_engine.trader_attributes["next_trade_date"]  # trade date of interest as string

    num_days_to_trade = 10
    day_counter = 0

    while day_counter < num_days_to_trade:

        # Fetch stock data of interest from FAANG Pulse AI API
        temp_date_selected = datetime.strptime(date_selected, "%Y-%m-%d") + timedelta(days=day_counter)  # datetime type operation

        stock_prices = trading_engine.get_stock_prices(tickers_list, datetime.strftime(temp_date_selected, "%Y-%m-%d"))
        #print(stock_prices)

        # Run trade execution logic using stock_prices
        trading_engine.run_trade_execution(stock_prices)

        day_counter += 1
        print(f"Day {day_counter} of {num_days_to_trade} completed.")


if __name__ == "__main__":

    live_trading()
    #test_trading()


    # Initializations:
    ## Stock tickers and their gradio dropdown string values.
    ## Read "trader_attributes.json" assign content to object variable
    ## ? A variable for backtesting or live testing mode.

    # Trade execution and update logic
    ## Get "next_trade_date" from "trader_attributes.json"
    ## Fetch stock data for all tickers for the "next_trade_date" over FAANG Pulse AI API (/get_prices_on_date)
    
    ## Run trade execution logic for each investor listed in "trader_attributes.json"
    ### For this investor, call /run_trend_prediction API to get the prediction result for each of the FAANG stocks.
    ### Run trading logic for this investor using the prediction result.
    ### Open this investor's current *.csv trade log file (find file name in "trader_attributes.json")
    ### According to this investor's trading strategy, perform trade for each of the FAANG stocks by adding new line for each stock ticker
    ### Note 1: The valid Actions are: HOLD, BUY, SELL
    ### Note 2: Check the last line of trade in log file. If it is the same as current trade date, skip the trade for this round (happens on holidays!)
    ### Note 3: If this investor has insufficient cash left AND the Action is a BUY, buy as much as possible and then perform a HOLD action instead.
    ### Close the updated trade log file for this investor.
