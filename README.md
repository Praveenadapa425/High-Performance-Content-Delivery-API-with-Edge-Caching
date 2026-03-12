# High-Performance Content Delivery API with Edge Caching

This repository implements a production-style content delivery API focused on low latency, strong HTTP caching, and CDN-first distribution.

## Status
- `Phase 1`: Completed
- `Phase 2-6`: Planned

See `docs/PHASES.md` and `docs/PHASE1.md` for details.

## Tech Stack
- API: FastAPI
- Database: PostgreSQL (Docker), SQLite fallback for local quick start/tests
- Object Storage: MinIO (S3-compatible)
- Container: Docker + docker-compose

## Implemented in Phase 1
- Core schema and models:
	- `Asset`
	- `AssetVersion`
	- `AccessToken`
- Endpoint:
	- `POST /assets/upload`
	- `GET /health`
- Strong ETag generation:
	- SHA-256 hash of file content during upload
- Storage flow:
	- Upload bytes to MinIO
	- Persist metadata + ETag in DB

## Local Run
1. Copy `.env.example` to `.env`.
2. Start services:

```bash
docker-compose up --build
```

3. API available at `http://localhost:8000`.

## Quick Test
```bash
pytest -q
```

## Example Upload
```bash
curl -X POST "http://localhost:8000/assets/upload" \
	-F "file=@./README.md" \
	-F "is_private=false"
```

## Submission Commands
Defined in `submission.yml`:
- `setup`
- `test`
- `benchmark`
