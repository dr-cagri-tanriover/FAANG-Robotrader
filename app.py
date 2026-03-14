import gradio as gr


with gr.Blocks(title="FAANG Robotrader", theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """
        # FAANG Robotrader

        **Work in progress in this space.**

        Check back later for updates.
        """
    )
    gr.Markdown("*Coming soon...*", elem_classes=["wip-note"])

app.launch()

