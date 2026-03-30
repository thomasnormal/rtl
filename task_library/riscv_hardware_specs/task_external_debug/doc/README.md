# External Debug Markdown

This directory contains a checked-in manual markdown transcription of the official RISC-V External Debug Support v0.13.2 PDF.

- Conversion model: `openai/gpt-5.4-mini` via the local `opencode` `converter` agent.
- Chunking: ordered 8-page source-PDF ranges for stability.
- Preprocessing: the final tail used 200-DPI page renders plus `pdftotext -layout` hint files, verified against page images.
- Reading order: `manifest.json`.
