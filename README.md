# NextRole: AI Resume & Job Matching Agent

NextRole parses a resume, compares it with a job description, explains skill gaps,
and produces an evidence-based role-targeted resume draft.

## AI provider setup

The backend uses OpenAI-compatible chat completion APIs and defaults to:

1. **Groq** as the primary provider.
2. **OpenRouter** as the automatic backup.
3. **Google Gemini** only when explicitly selected with `AI_PROVIDER=gemini`
   or enabled using `AI_ENABLE_GEMINI_FALLBACK=true`.

Add provider keys as Render environment variables. Never commit API keys.

Recommended Render variables:

- `AI_PROVIDER=groq`
- `GROQ_API_KEY=<your Groq key>`
- `GROQ_MODEL=openai/gpt-oss-120b`
- `OPENROUTER_API_KEY=<your OpenRouter key>`
- `OPENROUTER_MODEL=openai/gpt-oss-20b:free`
- `AI_REQUEST_TIMEOUT_SECONDS=8`

The app tries each configured provider once with a bounded timeout. It does not
waste the request budget repeatedly retrying a failing provider. If every
provider fails, the existing evidence-preserving local fallback remains active.

## Useful provider links

- Groq API keys and docs: https://console.groq.com/keys
- Groq model/rate-limit reference: https://console.groq.com/docs/rate-limits
- OpenRouter keys: https://openrouter.ai/keys
- OpenRouter free models: https://openrouter.ai/models?pricing=free

Free tiers have changing model availability and quotas. Check each provider's
dashboard before relying on a particular model for production traffic.

## Backend roadmap

Current foundations include FastAPI upload endpoints, PDF/DOCX/TXT extraction,
skill-alias matching, TF-IDF similarity, AI analysis, and an evidence-preserving
local tailoring fallback.

Highest-value backend gaps to address next:

1. Structured resume schema + validation before rendering.
2. DOCX/PDF export with selectable templates (the current UI download is text).
3. Resume parsing quality checks and OCR for scanned PDFs.
4. Authentication, per-user data isolation, consent and retention controls.
5. Rate limiting, upload throttling, and abuse protection.
6. Background job processing for long-running parsing/generation.
7. Persistent job/resume history and versioned tailored drafts.
8. Observability: request IDs, provider latency, failure reason, quota status,
   and endpoint-level metrics without logging resume contents or API secrets.
9. Evaluation suite with representative resumes/JDs, factuality checks,
   section-preservation checks, and regression tests.
10. Optional semantic retrieval/reranking for better skill and requirement
    matching beyond keyword overlap.

Do not add a vector database, Redis, Celery, or paid infrastructure until usage
justifies the operational cost. Start with measurable quality and reliability.
