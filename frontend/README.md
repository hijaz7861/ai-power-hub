# AI Power Hub Web

Initial Next.js workspace dashboard.

## Requirements

- Node.js 22+
- The FastAPI backend running at http://127.0.0.1:8000

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

The Next.js rewrite proxies `/api/*` and `/health` to the backend. Set API_BASE_URL if the backend runs elsewhere.

## Current scope

The page reads the backend health endpoint and provider catalogue. It does not yet implement user login, chat execution, payments, or AI generation. Roadmap cards are informational, not active product controls.
