# IMSIC Interrupt File Markdown

This directory contains the IMSIC-relevant subset of the checked-in manual markdown transcription of
the official RISC-V Advanced Interrupt Architecture v1.0 PDF.

- Conversion model: `gpt-5.4-mini` using the OpenAI API key from the local `.env`.
- Workflow: manual page-image conversion with the repository's PDF-to-markdown converter prompt as the
  transcription contract, then task-level curation to keep only the IMSIC sections.
- Reading order: `registers.md` first, then `manifest.json` for the longer source chunks.
