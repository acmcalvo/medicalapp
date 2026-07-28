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
