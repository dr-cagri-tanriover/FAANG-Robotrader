---
title: FAANG Robotrader
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.9.0
app_file: app.py
pinned: false
license: apache-2.0
---

# FAANG-Robotrader

## Application Summary
This application uses [FAANG Pulse AI](https://huggingface.co/spaces/ML-Owl/FAANG-Pulse-AI) ML inference engine under the hood and is created as a platform to evaluate how well the  inference engine performs in the real world over a period of time using previously unseen data. As part of this evaluation, 4 virtual personas each with different risk tolerance and stock investment strategy have been created to provide real world context into the evaluation process.

## Robotrader Architecture and Operation
Top level architecture of the robotrader is shown in [Figure 1](#fig1-arch-diagram). Following are the 3 core components of the system:

**1 -** FAANG Pulse AI Hugging Face Space  
**2 -** Github Workflows  
**3 -** FAANG Robotrader Hugging Face Space  


<div align=center>

<a id="fig1-arch-diagram"></a>

#### Figure 1 - System Architecture

<img src="docs/Robotrader_diagram.png" alt="Robotrader diagram" width="80%" />

</div>

Next, we will take a closer look at the role of each core component in the system.

**1 - FAANG Pulse AI Hugging Face Space**: This is the machine learning (ML) inference engine where my pre-trained Isolation Forest model runs. It includes a GUI (created using Gradio) and a public API. You can use the GUI to check trending information on each of FAANG stocks for any given day (starting from 2013) I would encourage you to [try the application](https://huggingface.co/spaces/ML-Owl/FAANG-Pulse-AI) using the GUI to get a better understanding of the API I will be explaining next.

This application exposes the following two API end points, which are very easy to use:  
- **/get_prices_on_date:** You provide a data and a list of FAANG stock tickers to this API, which will then return JSON data that includes the OHLCV data for each stock for the selected date. This API makes life easier for developers to acquire stock information without having to deal with the Yahoo finance API explicitly (note how Pulse AI talks to the Yahoo Finance API as shown in [Figure 1](#fig1-arch-diagram))

- **/run_trend_prediction:** This provides access to the ML inference engine on Pulse AI. You provide the stock ticker, date of interest and the decision threshold (i.e., the level of risk tolerance) to use, and the inference engine makes a prediction on whether the stock is trending up (TREND_UP), trending down (TREND_DOWN) or not trending at all (NO_TREND) based on the preceding 30 days (starting from the selected date) of price movements for that stock.

The robotrader application calls the above two API end points to get all the stock market related data as well as the ML trend predictions for the FAANG stocks.

**2 - GitHub Workflows**: You can think of Github Workflows as a programmable "conveyor belt" for your code. Whenever you do something in your repository (e.g., push new code or open a pull request), this conveyor belt automatically kicks in to perform repetitive tasks like testing, building, or deploying your project. Workflows are defined by simple **\*.yml** text files that are stored in a specific folder called *.github/workflows*. Essentially, workflows are your project's personal assistant that never sleeps and follows instructions perfectly.

In this application, as shown in [Figure 1](#fig1-arch-diagram), I created two workflows:

- **sync to HF:** When creating a space on Hugging Face, one normally uses it as a GitHub as well where all the code lives, and the GUI is executed. However, for people using the free version of Hugging Face, a space goes to sleep and becomes unresponsive after some time (typically 24 hours but this may vary). This means unless the space is woken up by a user visiting it, no background processes can be executed during sleep. Because the robotrader application needs to automatically access the real-world pricing information and update its internal trader logs once a day after the markets close, this imposed sleep function on Hugging Face is a showstopper.

    In order to get around the above issue, I created a GitHub repository, whose mirror is pushed to the Hugging Face repository, where the results are served using the gradio GUI in the space created. In this arrangement, I make all my core modifications and updates on my Github repository and push my changes to it. When the "sync to HF" workflow notices the change to my Github repo (which is almost instantaneous), all of the changes are immediately pushed to the Hugging Face mirror repository. Any change on the Hugging Face repo triggers an auto rebuild (which is entirely managed by Hugging Face), after which the space restarts to reflect the new changes. 

- **daily cron:** This workflow executes the *trading_logic.py* script once each day after the US stock market closes, and executes the trades based on each investor's strategy. The trade log of each investor (as a \*.csv file) is also updated automatically.
    
    After the trade log of each investor is updated, these changes are automatically staged, committed and pushed to the Hugging Face (mirror) repository. When the Hugging Face receives the changes, it automatically rebuilds the space, after which the most up to date information is served to the users via the GUI. 

Thanks to the above two workflows, the Github repository and Hugging Face repository remain in sync at all times.

**3 - FAANG Robotrader Hugging Face Space:** To understand the operation of the robotrader, let's start with the two core functions it runs as illustrated in [Figure 1](#fig1-arch-diagram).

- **Trading Logic:** This is the part that is auto-executed once a day to fetch the current prices for FAANG stocks and to execute BUY, SELL, or HOLD actions for each investor depending on the risk tolerance and the investment strategy defined for each. This module also keeps track of each trade transaction of each trader in a dedicated \*csv file, which is the central source of information the user interface uses to generate a number of evaluation reports.

    As described in the workflow section above, the trading logic is called and executed on Github repository automatically, which also does not use any Hugging Face compute resources. 😉 Once the required computations are completed on Github, the updated \*.csv files are simply pushed to Hugging Face repository to keep everything in sync.

- **The User Interface (GUI):** The user interface is the mechanism whereby the trade log of each investor is evaluated by generated reports on demand. Please note the actions performed on the GUI use the information provided in each \*.csv file, which is updated once daily by the Trading Logic process.

    The GUI is intentionally kept simple with one interactive drop down menu for the user. Each menu selection triggers the generation of a table that is displayed below the drop down menu. Next let's take a close look at each menu item and see how to interpret the information displayed on each displayed table.

    - **Trade Actions Summary:** This option generates a table with a high level view of the executed trades for each investor by the robotrader. Table includes the following columns:
        - ***Investor***: Includes the name of investors.
        - ***Start Date***: This is the date of the first trade transaction for an investor. We expect this to be the same for all investors to allow a fair comparison.
        - ***End Date***: This is the last date on the transaction record for an investor. End Date for all investors is expected to be the same and is updated each day.
        - ***HOLD Trades (%)***: For this column two information fields per cell are included. The first one gives the total count of all HOLD transactions executed while the second one in paranthesis is the percentage of HOLD trades for the investor. Note this count is an aggregation of all of the 5 FAANG stock transactions for the investor.
        - ***SELL Trades (%)***: This is the same as HOLD column but exclusively for all the SELL transactions for an investor.
        - ***BUY Trades (%)***: This is the same as HOLD and SELL columns but exclusively for all the BUY transactions for an investor.
        - ***Shares Owned***: The total number of all FAANG shares owned on the End Date for an investor are listed in this column.

    - **Cash Status:** This is the second option in the drop down menu, which generates a table summarizing the cash outlook of each investor. Following columns are included in this table.
        - ***Investor***: Includes the name of investors.
        - ***Start Date***: This is the date of the first trade transaction for an investor. We expect this to be the same for all investors to allow a fair comparison.
        - ***End Date***: This is the last date on the transaction record for an investor. End Date for all investors is expected to be the same and is updated each day.
        - ***Starting Cash ($)***: Each investor's starting cash allocation for the robotrade is listes in US Dollars in this column. The starting cash is fixed at $500,000 for each investor for a fair comparison.
        - ***Value of Shares Owned ($)***: This is the combined dollar amount for all owned FAANG shares by an investor calculated based on the End Date sell price for each stock.
        - ***Investable Cash ($)***: The remaining cash that is left for investing from the Starting Cash amount (after all the the buy and sell trades until the End Date)
        - ***Portfolio Value ($)***: This is the dollar amount of the Value of Shares owned and the Investable Cash. When this amount exceeds the Starting Cash, an investor will have positive ROI.
        - ***Projected Return ($ (%))***: This column summarizes the gain/loss of an investor if they were to sell all the shares they owned at the End Date price for ***each owned FAANG stock***. There are two figures per cell in this column; one is the dollar amount and the other is the percentage relative to the Starting Cash. Gain is color coded with green, while red indicates a loss. Orange indicates a neutral standing.

    - **Per Stock Returns:** This option in the drop down menu generates a table summarizing the cash outlook of each investor based on each of the FAANG stocks. In other words, this information is a mixture of the Cash State and the Trade Actions provided on a per stock basis. Following columns are included in this table. Let's take a look at each of the columns in this table to get a clearer understanding of the information presented.
        - ***Investor***: Includes the name of investors.
        - ***Ticker***: The ticker symbol of the FAANG stock.
        - ***Start Date***: This is the date of the first trade transaction for an investor. We expect this to be the same for all investors to allow a fair comparison.
        - ***End Date***: This is the last date on the transaction record for an investor. End Date for all investors is expected to be the same and is updated each day.
        - ***Shares Owned***: The number of shares for a given ticker the investor currently has.
        - ***But Total ($)***: Total dollar amount an investor has spent on buying the shares of a FAANG company with the specified ticker.
        - ***Sell Total ($)***: Total dollar amount an investor has earned by selling the shares of a FAANG company with the specified ticker.
        - ***Projected Return ($ (%))***: This column summarizes the gain/loss of an investor ***on a particular stock (specified by the ticker)*** if they were to sell  the shares they owned at the End Date price. There are two figures per cell in this column; one is the dollar amount and the other is the percentage relative to the Starting Cash. Gain is color coded with green, while red indicates a loss. Orange indicates a neutral standing.

## Meet the Traders

There are 4 virtual traders I created each with a different investment strategy and risk tolerance. Let's meet each of them and how they trade using the robotrader.

- **Safe Sam**

- **Optimal Owen**

- **Brave Beth**

- **Random Randy**
