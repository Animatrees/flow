# Flow

Flow is a **project management / profiles dashboard** service for creating, updating, sharing, and deleting project information, including project details and attached documents.

## Status

This project is in the **early development stage**.  
Core business functionality is not implemented yet; the repository currently contains the initial project skeleton, development tooling setup, and a minimal API health endpoint.

## Current Implementation

- FastAPI application bootstrap in `main.py`
- Health check endpoint:
  - `GET /health` -> `{"status": "ok", "service": "flow"}`

## Planned Features

- Project profile management (create, update, delete)
- Project information sharing
- Support for attached project documents

## Tech Stack

- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic
- Dishka
- Uvicorn

## Development Setup

### Prerequisites

- Python 3.12+
- `uv` package manager

### Install Dependencies

```bash
uv sync --all-groups
```

### Run Locally

```bash
make run
```

Then open `http://127.0.0.1:8000/health`.

## Useful Commands

```bash
# Run app locally
make run

# Run all checks
make check

# Run linters/format/type checks
make precommit

# Run tests
make test
```

## Project Structure

```text
src/       # Application source code
tests/     # Unit and other tests
main.py    # FastAPI app entry point (includes /health)
```

## Roadmap (Initial)

- Define domain models for projects and profiles
- Implement CRUD endpoints for project entities
- Add document attachment handling
- Add database migrations and integration tests
- Introduce authentication/authorization
