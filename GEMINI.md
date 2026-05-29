# Gemini Context & Project Details

This file captures project-specific details and implementation context for the **The Hindu ePaper Reader** project.

## Recent Features

### AI Editor's Picks (`/api/top-headlines`)
- Implemented `/api/top-headlines` to retrieve and rank daily headlines using OpenRouter's free tier LLMs.
- Cache mechanism: writes outputs to `*_top.json`. Validity depends on the presence and freshness of the main cache (`*.json`).
- OpenRouter Configuration:
  - Header Title: `The Hindu ePaper Reader`
  - Referer: `https://github.com/kushagra-gupta-kg01/the-hindu-epaper-reader`
  - Models fallback list: `["z-ai/glm-4.5-air:free", "openrouter/owl-alpha", "google/gemma-4-31b-it:free"]` (limited to 3 items max per OpenRouter requirements).
  - Timeout: 8 seconds (leaving 2s buffer for Vercel's 10s serverless limit).
- Self-Healing Scrapes: if main headlines cache is missing, endpoint triggers `service.get_headlines` internally before LLM generation.
- ID Normalization: case-insensitive suffix-stripping matching (e.g., matching `go1g1nqtf` to `GO1G1NQTF.1`).

## Testing Paradigms
- Strictly maintain **100% test coverage** on all Python backend code.
- Run unit tests: `PYTHONPATH=. .venv/bin/pytest tests/ -m "not e2e"`
- Run E2E tests: `OPENROUTER_API_KEY="..." PYTHONPATH=. .venv/bin/pytest tests/`
