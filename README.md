# Medical Interaction Assistant

Python-first medical workflow app for medication interaction checking and clinician/pharmacist advice.

## Stack

- Backend: FastAPI
- Data layer: PostgreSQL-ready SQLAlchemy models
- Clinical integrations: RxNav, DailyMed, openFDA
- AI explanation layer: Azure OpenAI-compatible interface
- Frontend: Next.js + TypeScript + MUI

## Repository Layout

- `backend/`: FastAPI API, services, and tests
- `frontend/`: Next.js app shell

## Quick Start

Backend and frontend are scaffolded for local development. Install dependencies in each folder and run the matching dev server.

## Run With Docker

This repository now includes container definitions for both services:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

Build and start everything:

```bash
docker compose up --build
```

App URLs:

- Frontend: `http://localhost:3000`
- Backend health check: `http://localhost:8000/health`

Stop containers:

```bash
docker compose down
```

## Optional External Interaction Provider

The backend can use an external interaction API and fall back to built-in high-risk rules when unavailable.

Set these backend environment variables:

- `INTERACTION_PROVIDER=auto` (default), `external`, or `rxnav`
- `INTERACTIONS_API_URL` (full HTTPS endpoint)
- `INTERACTIONS_API_KEY` (optional)
- `INTERACTIONS_API_AUTH_HEADER` (optional, default: `Authorization`)
- `INTERACTIONS_API_TIMEOUT_SEC` (optional, default: `10`)

When external provider is configured and returns results, UI source labels show `External API`.

### RxLabelGuard Example

Use these backend environment variables in Render:

- `INTERACTION_PROVIDER=external`
- `INTERACTIONS_API_URL=https://api.rxlabelguard.com/v1/interactions`
- `INTERACTIONS_API_KEY=<your_rxlabelguard_key>`
- `INTERACTIONS_API_AUTH_HEADER=Authorization`

## Bulk Fallback Interaction Rules (No API Key Required)

You can maintain many interaction pairs at once through a JSON file instead of editing Python rules one by one.

- Default file: `backend/app/data/interaction_rules.json`
- Optional override: `HEURISTIC_RULES_FILE=/absolute/path/to/interaction_rules.json`

Each rule must include:

- `drug_a`, `drug_b`
- `keywords_a`, `keywords_b` (arrays of match keywords)
- `severity` (`contraindicated|major|moderate|minor|none`)
- `mechanism`, `clinical_effect`, `recommendation`
- `monitoring` (array of strings)

This allows fast bulk updates by replacing or extending the JSON file.

## Condition + Medication Risk Rules

You can also maintain condition-aware risk checks (for example `diabetes + prednisone`, `lung cancer + bleomycin`) through a JSON file.

- Default file: `backend/app/data/condition_medication_rules.json`
- Optional override: `CONDITION_MEDICATION_RULES_FILE=/absolute/path/to/condition_medication_rules.json`

Each rule must include:

- `condition`, `medication`
- `condition_keywords`, `medication_keywords` (arrays of match keywords)
- `severity` (`contraindicated|major|moderate|minor|none`)
- `mechanism`, `clinical_effect`, `recommendation`
- `monitoring` (array of strings)

In the UI, enter conditions in the new `Conditions / diagnoses` field as a comma-separated list (example: `diabetes, lung cancer`).
