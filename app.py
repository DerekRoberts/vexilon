import os
import gradio as gr

def chat_fn(message, history, persona):
    # A generic placeholder for the future RAG functionality
    return f"Vexilon ({persona} Mode) received: {message}"

with gr.Blocks(title="BCGEU Navigator", fill_height=True) as demo:
    with gr.Row():
        gr.HTML("<div style='display: flex; height: 100%; align-items: center;'><h3 style='margin: 0;'>BCGEU Navigator</h3></div>")
        persona = gr.Dropdown(
            choices=["Lookup", "Grieve", "Manage"],
            value="Lookup",
            show_label=False,
            container=False,
            min_width=100
        )
    
    gr.ChatInterface(
        fn=chat_fn,
        chatbot=gr.Chatbot(show_label=False),
        additional_inputs=[persona],
        fill_height=True
    )

    gr.HTML("""
        <div style="text-align: center; color: #6b7280; font-size: 0.85rem; padding-top: 10px;">
            <a href="https://github.com/DerekRoberts/vexilon" target="_blank" style="color: #3b82f6; text-decoration: none;">GitHub</a>
            &nbsp;&nbsp;•&nbsp;&nbsp;
            <a href="https://github.com/DerekRoberts/vexilon/blob/main/docs/PRIVACY.md" target="_blank" style="color: #3b82f6; text-decoration: none;">Privacy</a>
            &nbsp;&nbsp;•&nbsp;&nbsp;
            <span>Dev mode</span>
        </div>
    """)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
    )
