import logging

import gradio as gr

from src.agent import RAGAgent


class GradioApp:
    """Gradio-based UI to interactively test the RAG retrieval system."""

    def __init__(self, agent: RAGAgent, logger: logging.Logger):
        self._agent = agent
        self._logger = logger
        self._interface: gr.Blocks = None

    def setup(self) -> None:
        """Build the Gradio Blocks interface."""
        self._logger.info("Setting up Gradio interface.")

        with gr.Blocks(
            title="RAG Retrieval Tester",
            theme=gr.themes.Soft(),
        ) as interface:
            gr.Markdown("## 🔍 RAG Retrieval Tester\nAsk a question and see the retrieved context and generated answer.")

            with gr.Row():
                question_input = gr.Textbox(
                    label="Question",
                    placeholder="Enter your question here...",
                    lines=2,
                    scale=4,
                )
                submit_btn = gr.Button("Submit", variant="primary", scale=1)

            answer_output = gr.Textbox(label="Answer", lines=6, interactive=False)

            with gr.Accordion("📄 Source Documents", open=False):
                sources_output = gr.Markdown()

            def run_query(question: str):
                if not question.strip():
                    return "Please enter a question.", ""
                result = self._agent.run(question)
                sources_md = self._format_sources(result.source_documents)
                return result.answer, sources_md

            submit_btn.click(
                fn=run_query,
                inputs=[question_input],
                outputs=[answer_output, sources_output],
            )
            question_input.submit(
                fn=run_query,
                inputs=[question_input],
                outputs=[answer_output, sources_output],
            )

        self._interface = interface
        self._logger.info("Gradio interface ready.")

    def _format_sources(self, documents) -> str:
        """Format source documents as readable Markdown."""
        if not documents:
            return "_No source documents were retrieved._"
        lines = []
        for i, doc in enumerate(documents, start=1):
            meta = ", ".join(f"**{k}**: {v}" for k, v in doc.metadata.items()) if doc.metadata else "_no metadata_"
            lines.append(f"**Source {i}** — {meta}\n\n> {doc.content}\n")
        return "\n---\n".join(lines)

    def launch(self) -> None:
        """Start the Gradio server."""
        self._logger.info("Launching Gradio app.")
        self._interface.launch()
