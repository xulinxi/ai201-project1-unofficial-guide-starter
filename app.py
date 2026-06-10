"""Gradio web UI for The Unofficial Guide. Run `python app.py` and open
http://localhost:7860. The CLI alternative is `python query.py`."""

import gradio as gr

from query import ask


def handle_query(question):
    if not question.strip():
        return "", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources or "(no sources — question is outside my documents)"


with gr.Blocks(title="The Unofficial Guide") as demo:
    gr.Markdown(
        "# The Unofficial Guide\n"
        "Ask about frosh life at Stanford — housing, dining, bikes, courses. "
        "Answers come only from a small corpus of Reddit threads and Stanford "
        "Daily articles (2013–2021), with sources cited."
    )
    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. Can I use a meal swipe at two dining halls in one meal period?",
    )
    btn = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

if __name__ == "__main__":
    demo.launch()
