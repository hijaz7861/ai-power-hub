# Initial Architecture

## Current implementation boundary

This first engineering slice establishes only the HTTP application shell and liveness/readiness probes. It does not yet implement authentication, persistence, provider calls, billing, credits, or production readiness.

## Planned request flow

Client -> API authentication/authorization -> request validation -> credit reservation -> provider orchestration -> usage settlement -> response.

## Architectural decisions

- Start with a modular monolith to reduce early operational complexity.
- Keep provider adapters isolated behind a common interface.
- Keep secrets in deployment environment/secret storage; never commit real credentials.
- Treat credit reservation and settlement as transactional operations when the billing subsystem is introduced.
- Add readiness checks only when real infrastructure dependencies exist.

## Local development

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
python -m pytest -q
```
