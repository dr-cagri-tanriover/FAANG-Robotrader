
import gradio as gr


with gr.Blocks(theme=gr.themes.Soft()) as dashboard:
    # The wrapper for everything in the launched demo.

    gr.Markdown("# FAANG Robotrader - *Safe Sam, Optimal Owen & Brave Beth's Race to the Top!*")

    gr.Markdown("""## Watch how well three different investors each with $500K budget perform in the real world using my Robotrader based on <a href="https://huggingface.co/spaces/ML-Owl/FAANG-Pulse-AI" target="_blank">FAANG Pulse AI !</a>
    
    ### 📣 Stay tuned for updates!!!""")

    
    # with gr.Row():
    #     with gr.Group():
    #         gr.Markdown("### 🙋🙋‍♂️🙋‍♀️ INVESTORS LIST:")
    #         investors_dropdown = gr.Dropdown(
    #         label="Choose an investor to assess.",
    #         value=ifeObj.stock_selected, choices=["APPLE", "AMAZON", "GOOGLE", "NETFLIX", "META (a.k.a. Facebook)"],
    #         #info="Pick one of 5 stocks of interest."
    #         )

    dashboard.launch()


    # Visualization and report out logic (will be driven by the gradio UI)
    ## Create a dropdown for each investor listed in "trader_attributes.json"
    ### Display time related trading info for this investor (e.g., start/end dates, number of total, HOLD, SELL and BUY trade days)
    ### Display cash related info for this investor. (e.g., total start cash, current value of shares owned, total cash left)
    ### Display returns for each FAANG stock (e.g. for each stock: total spent via BUY actions, total return via SELL actions, %return = (SELL-BUY)/BUY)

    #Date,Ticker,Price,Direction,Action,Shares,Cash Before Trade,Cash After Trade