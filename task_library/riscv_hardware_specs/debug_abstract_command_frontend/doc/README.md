# Debug Abstract Command Frontend Markdown

This directory contains the abstract-command-relevant subset of the checked-in manual markdown
transcription of the official RISC-V External Debug v0.13.2 PDF.

- Conversion model: `gpt-5.4-mini` using the OpenAI API key from the local `.env`.
- Workflow: manual page-image conversion with the repository's PDF-to-markdown converter prompt as the
  transcription contract, then task-level curation to keep only the abstract-command sections.
- Reading order: `registers.md` first, then `manifest.json` for the longer source chunks.
