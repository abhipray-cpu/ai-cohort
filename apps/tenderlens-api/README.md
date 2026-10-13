# TenderLens API

The Day 1 API will accept tender documents, orchestrate structured extraction through the local Codex runtime, validate results, and expose review-ready bid briefs.

The API now supports opportunity creation, PDF upload, queued extraction, review decisions, run history, and approved JSON export. The worker calls the installed Codex CLI through the shared adapter. See the repository README for local commands and `docs/tenderlens/` for release gates. OCR requires an available Tesseract installation; unreadable pages are surfaced as a failed job until OCR is available.
