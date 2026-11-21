# NextRole: AI Resume & Job Matching Agent

NextRole parses a resume, compares it with a target job description, explains skill gaps, and produces an evidence-based tailored resume draft.

## Current capabilities

- FastAPI endpoints for text matching, file matching, resume tailoring, and health checks.
- PDF, DOCX, TXT, and Markdown text extraction (scanned image-only PDFs require OCR and are rejected with a clear message).
- Skill alias matching and TF-IDF text similarity.
- AI-generated resume drafts with deterministic quality gates.
- Evidence-preserving local fallback when AI is unavailable or a generated draft fails validation.
- ATS-oriented single-column PDF and DOCX exports, plus plain-text download.
- Clickable email, phone, LinkedIn, GitHub, and portfolio links where present in source text.
- 10 MB upload limit.

## Resume quality gate

Before an AI-generated draft is rendered, NextRole checks that it:
- Is not empty or suspiciously short.
- Does not introduce skills absent from the source resume.
- Preserves dates and numeric facts found in the source.
- Preserves source email addresses and profile/portfolio URLs.

A failed check switches to the deterministic evidence-preserving fallback. This is a conservative safety net, not a guarantee that every semantic claim is true. Candidates must review the final document before applying. NextRole does not claim a guaranteed ATS score or compatibility with every employer's parsing system.

## Local development

Use Python 3.12:

```powershell
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000.

## AI provider configuration

The backend uses OpenAI-compatible chat completion APIs and defaults to Groq, then OpenRouter. Gemini is only used when explicitly selected or enabled.

Set provider keys as environment variables. Never commit API keys.

- `AI_PROVIDER=groq`
- `GROQ_API_KEY=<your Groq key>`
- `GROQ_MODEL=openai/gpt-oss-20b`
- `OPENROUTER_API_KEY=<your OpenRouter key>` (optional backup)
- `OPENROUTER_MODEL=openai/gpt-oss-20b:free`
- `AI_REQUEST_TIMEOUT_SECONDS=8`

Provider model availability and free-tier quotas change. If no provider key is configured, matching and evidence-based fallback still work, but AI analysis/tailoring uses fallback output.

## Deployment

The repository includes a Render Blueprint in `render.yaml` and a Dockerfile. Configure the secret provider keys in the Render dashboard. The health check is `/health`. Render deployment requires the GitHub repository to be connected to the Render service and the required secrets to be configured.

## Known limitations before production use

- Scanned/image-only PDFs need OCR; OCR is not bundled.
- No user authentication, persistent resume history, or application tracking.
- No explicit per-user data isolation because the app currently stores no user records.
- No request rate limiter or abuse-protection layer yet.
- Skill matching is alias/keyword based and TF-IDF based, not a complete semantic assessment.
- Quality gates detect selected classes of omissions and unsupported skills; they cannot prove every generated sentence is factually correct.
- PDF and DOCX layouts are ATS-oriented but no single format is guaranteed to parse identically in every ATS.

Never treat a match percentage as a hiring probability. Review the generated resume and verify every claim before submitting it.
