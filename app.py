import os
import gradio as gr

def chat_fn(message, history, persona):
    # A generic placeholder for the future RAG functionality
    return f"Vexilon ({persona} Mode) received: {message}"

demo = gr.ChatInterface(
    fn=chat_fn,
    title="Vexilon",
    description="Standard Gradio Interface",
    additional_inputs=[
        gr.Dropdown(
            choices=["Lookup", "Grieve", "Manage"],
            value="Lookup",
            label="Operational Role"
        )
    ],
    fill_height=True
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
    )
