# Backend

FastAPI service for the medical interaction assistant.

## RxLabelGuard configuration

Set these environment variables when you want the backend to query RxLabelGuard:

- `RXLABELGUARD_BASE_URL` - base URL for the service
- `RXLABELGUARD_QUERY_PATH` - request path for label lookup, defaults to `/labels/search`
- `RXLABELGUARD_API_KEY` - optional API key or token
- `RXLABELGUARD_API_KEY_HEADER` - optional header name, defaults to `Authorization`
- `RXLABELGUARD_API_KEY_PREFIX` - optional prefix for `Authorization`, defaults to `Bearer`

## Local env example

Copy `backend/.env.example` to `backend/.env` and fill in your values before running the backend locally.
