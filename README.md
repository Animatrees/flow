# Flow – Project Management service

**Flow** is a backend service designed for project and document management. It allows users to create projects, invite
participants, manage project metadata, and securely attach or download project-related documents (PDF, DOCX).

This project was developed as part of a mentorship course to practice modern Python backend development, advanced cloud
infrastructure (AWS), and system architecture.

---

## Table of Contents

- [Features Overview](#-features-overview)
- [Architecture & Applied Knowledge](#architecture--applied-knowledge)
- [Tech Stack](#tech-stack)
- [API Endpoints](#api-endpoints)
- [Local Development Setup](#local-development-setup)
- [Running with Docker Compose](#running-with-docker-compose)
- [Database Migrations](#database-migrations)
- [Testing](#testing)
- [CI/CD](#cicd)
- [AWS Deployment](#aws-deployment)
- [Project Structure](#project-structure)
- [License](#license)

---

## ✨ Features Overview

### 1. Implemented Core Requirements

*Note: The actual API endpoints differ from the initial specification to adhere to strict RESTful design principles and
improve security/scalability. This was done upon agreement with the mentor.*

* **User Authentication:** Registration and Login flows returning a standard OAuth2 Bearer JWT.
* **Project Management:** Users can Create, Read, Update, and Delete projects. Creating a project automatically grants
  the user `Owner` access.
* **Project Sharing:** Project owners can invite other registered users to the project via their username, granting them
  `Member` (participant) access. Owners have full control; members can modify project details and upload/delete their own
  documents, but cannot delete the project or add new members.
* **Document Management:** End-to-end support for uploading and downloading `.pdf` and `.docx` files linked to projects.
* **JSON Standard:** All business logic endpoints strictly accept and return JSON payloads.

### 2. Completed Optional Requirements

- **Full Pydantic validation:** all request and response schemas use Pydantic v2; input is validated at the schema
  level (type coercion, constraints, cross-field validators).
- **JWT auth with RSA keys:** tokens are signed with RS256 (private key) and verified with the corresponding public key;
  the upload-intent flow reuses the same JWT service with a dedicated `upload_intent` token type.
- **Modern Package Management:** Used `uv` (a modern, fast alternative to poetry) with `pyproject.toml` for strict
  dependency locking and environment management.
- **Test coverage:** unit tests (with fakes/stubs) and integration tests (SQLite + HTTPX TestClient) for auth, users,
  projects, and documents.
- **CI/CD bindings:** GitHub Actions pipelines for testing and release.
- **Docker:** multi-stage Dockerfile and Docker Compose files for local and production environments.

### 3. Features Beyond the Specification

- **Self-service user management:** users can view, update, and delete their own accounts via `/users/me`.
- **Soft delete for users:** instead of a hard delete, `DELETE /users/me` anonymizes the account (username, email, and
  password hash are overwritten; `is_active` set to false; `deleted_at` timestamp recorded). Deleted users cannot log
  in. Projects they own are cascade-deleted; their memberships are removed.
- **Admin panel:** superuser-only routes (`/admin/users`) for viewing and managing any user account, including toggling
  `is_superuser` and `is_active` flags. Routes are excluded from the public OpenAPI schema.
- **Password strength validation:** `zxcvbn` is used during registration to reject weak passwords before hashing.
- **Argon2 password hashing:** industry-standard memory-hard hashing algorithm.
- **Project status and dates:** projects carry `status` (`open` / `wip` / `done`), `start_date`, and `end_date` fields;
  a DB-level `CHECK` constraint enforces `end_date >= start_date`.
- **Checksum support:** clients may provide a checksum on upload confirmation for integrity verification.
- **Two-step presigned upload flow:** avoids routing binary file payloads through the application server; the upload
  token is JWT-signed and bound to both the project and the uploading user.
- **UUIDv7 primary keys:** time-ordered UUIDs used for all entity IDs.
- **Architecture boundary enforcement:** `tach` is wired into pre-commit to prevent circular or invalid cross-layer
  imports.
- **pgAdmin** in the local Docker Compose stack for visual DB inspection.
- **Production CloudFormation template:** VPC, public/private subnets, RDS (PostgreSQL), EC2 auto-scaling group, S3
  buckets (documents + deployment artifacts), IAM roles with least-privilege policies, GitHub Actions OIDC integration.
- **Automated EC2 deployment via SSM:** the release workflow packages a deployment bundle, uploads it to S3, and
  triggers the deployment shell script on the EC2 instance using AWS SSM `send-command` (no SSH required).

---

## Architecture & Applied Knowledge

Throughout the development of this project, several advanced backend patterns were applied:

1. **Layered Architecture:** The codebase is strictly divided into Domain (Schemas/Contracts), Services (Business
   Logic), API (HTTP/Routers), and Database (SQLAlchemy/Repositories). Services know nothing about HTTP requests.
2. **Repository Pattern:** Database operations are abstracted away behind Repository interfaces. This allows seamless
   switching between the PostgreSQL production database and the in-memory `aiosqlite` database used for lightning-fast
   integration tests.
3. **Dependency injection:** Dishka container with scoped providers wired to the FastAPI request lifecycle; services and
   repositories injected via `FromDishka`.
4. **Asynchronous Programming:** Fully asynchronous stack from the database driver (`asyncpg`/`aiosqlite`) up to the
   FastAPI routes and AWS S3 interactions (`aioboto3`).
5. **Automated Testing:** Extensive Unit and Integration tests written with `pytest`. Fakes and mocks are used to
   isolate S3 storage and Database layers when testing business rules.
6. **GitHub Actions:** multi-job workflows with job dependencies, matrix reuse, OIDC-based AWS authentication (no stored
   secrets), artifact passing between jobs.
7. **AWS CloudFormation (IaC):** VPC networking, RDS, EC2 launch templates, auto-scaling groups, S3 bucket policies, IAM
   role chaining, OIDC provider for GitHub.
8. **AWS SSM Parameter Store:** sensitive production values (DB password, JWT keys) are stored in Parameter Store and
   fetched by the deploy script at runtime; the repository stores only the CloudFormation stack name.
9. **Code quality toolchain:** Ruff (linting + formatting), ty (type checking), tach (architectural boundary
   enforcement), pre-commit hooks, all wired into CI.

---

## Tech Stack

| Layer                    | Technology                                             |
|--------------------------|--------------------------------------------------------|
| Language                 | Python 3.12+                                           |
| Web framework            | FastAPI 0.135                                          |
| ORM                      | SQLAlchemy 2.x (async)                                 |
| Migrations               | Alembic                                                |
| Database                 | PostgreSQL 17 (production), SQLite + aiosqlite (tests) |
| Dependency injection     | Dishka                                                 |
| Auth                     | PyJWT (RS256), Argon2 password hashing                 |
| File storage             | AWS S3 via aioboto3                                    |
| Package manager          | uv                                                     |
| Containerization         | Docker + Docker Compose                                |
| CI/CD                    | GitHub Actions                                         |
| Cloud infrastructure     | AWS (EC2, RDS, S3, VPC, IAM) via CloudFormation        |
| Linting / formatting     | Ruff                                                   |
| Type checking            | ty                                                     |
| Architecture enforcement | tach                                                   |

---

## API Endpoints

A fully interactive Swagger UI documentation is automatically generated and available at `/docs` when running the
application.

### Authentication

| Method | Endpoint                | Description                             |
|:-------|:------------------------|:----------------------------------------|
| `POST` | `/api/v1/auth/register` | Register a new user account.            |
| `POST` | `/api/v1/auth/login`    | Authenticate and retrieve a Bearer JWT. |

### User Profiles (Protected)

| Method   | Endpoint                  | Description                                           |
|:---------|:--------------------------|:------------------------------------------------------|
| `GET`    | `/api/v1/users/me`        | Retrieve the authenticated user's profile.            |
| `PATCH`  | `/api/v1/users/me`        | Update the user's username or email.                  |
| `DELETE` | `/api/v1/users/me`        | Soft-delete the user's account and cleanup resources. |
| `GET`    | `/api/v1/users/{user_id}` | Retrieve public profile information of a user.        |

### Projects (Protected)

| Method   | Endpoint                        | Description                                                |
|:---------|:--------------------------------|:-----------------------------------------------------------|
| `POST`   | `/api/v1/projects`              | Create a new project (caller becomes the Owner).           |
| `GET`    | `/api/v1/projects`              | List all projects the user has access to.                  |
| `GET`    | `/api/v1/projects/{project_id}` | Retrieve detailed information about a specific project.    |
| `PATCH`  | `/api/v1/projects/{project_id}` | Update project details (accessible to Owners and Members). |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete a project entirely (Owner only).                    |

### Project Members (Protected)

| Method | Endpoint                                                | Description                                            |
|:-------|:--------------------------------------------------------|:-------------------------------------------------------|
| `GET`  | `/api/v1/projects/{project_id}/members`                 | List all members (and their roles) of a project.       |
| `POST` | `/api/v1/projects/{project_id}/members?user={username}` | Invite a user to the project as a Member (Owner only). |

### Documents (Protected)

| Method   | Endpoint                                                 | Description                                                                          |
|:---------|:---------------------------------------------------------|:-------------------------------------------------------------------------------------|
| `GET`    | `/api/v1/projects/{project_id}/documents`                | List all documents attached to a project.                                            |
| `POST`   | `/api/v1/projects/{project_id}/documents/upload-intents` | Request a presigned URL and secure token to upload a file directly to AWS S3.        |
| `POST`   | `/api/v1/projects/{project_id}/documents`                | Confirm a successful S3 upload and save file metadata to the database.               |
| `GET`    | `/api/v1/documents/{document_id}`                        | Retrieve document metadata.                                                          |
| `GET`    | `/api/v1/documents/{document_id}/download-url`           | Generate a secure, time-limited presigned URL to download the file directly from S3. |
| `PATCH`  | `/api/v1/documents/{document_id}`                        | Update document metadata (e.g., rename).                                             |
| `DELETE` | `/api/v1/documents/{document_id}`                        | Delete a document from the database and trigger file removal in S3.                  |

### Admin Users (Superuser Only - Hidden from Swagger)

| Method   | Endpoint                        | Description                                                  |
|:---------|:--------------------------------|:-------------------------------------------------------------|
| `GET`    | `/api/v1/admin/users`           | List all users (including soft-deleted/inactive).            |
| `GET`    | `/api/v1/admin/users/{user_id}` | Get detailed admin view of a specific user.                  |
| `PATCH`  | `/api/v1/admin/users/{user_id}` | Modify user roles (e.g., grant superuser) and active status. |
| `DELETE` | `/api/v1/admin/users/{user_id}` | Administratively soft-delete a user.                         |

---

## Local Development Setup

### Prerequisites

* Python 3.12+
* [`uv`](https://docs.astral.sh/uv/) package manager
* Docker & Docker Compose
* AWS credentials configured locally (for S3 integration)
* Make

### Install Dependencies

```bash
uv sync --dev
```

### Configure Environment

Copy the example env file and fill in the values:

```bash
cp .env.example .env
```

Key variables:

```env
# Database
DB__NAME=flow
DB__USER=flow
DB__PASSWORD=your_password
DB__HOST=localhost
DB__PORT=5432
 
# JWT — generate RSA key pair and point to the files
JWT__PRIVATE_KEY_PATH=/path/to/jwt-private.pem
JWT__PUBLIC_KEY_PATH=/path/to/jwt-public.pem
 
# S3
S3__BUCKET=your-bucket-name
S3__REGION=eu-north-1
S3__PRESIGN_EXPIRE_SECONDS=900
```

### Generating RSA Key Pair

```bash
mkdir -p secrets/dev
openssl genrsa -out secrets/dev/jwt-private.pem 2048
openssl rsa -in secrets/dev/jwt-private.pem -pubout -out secrets/dev/jwt-public.pem
```

### Apply Migrations

```bash
make migrate
```

### Run the Development Server

```bash
make run
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`
---

## Running with Docker Compose

The Compose stack includes the application, PostgreSQL, and pgAdmin.

```bash
cp .env.docker.example .env.docker
# Fill in .env.docker — DB__HOST should be "postgres"
```

The JWT keys are mounted as secrets:

```bash
mkdir -p secrets/dev
# Place jwt-private.pem and jwt-public.pem in secrets/dev/
```

Start all services:

```bash
docker compose up --build
```

| Service    | URL                          |
|------------|------------------------------|
| API        | `http://localhost:8000`      |
| Swagger UI | `http://localhost:8000/docs` |
| pgAdmin    | `http://localhost:5050`      |

---

## Database Migrations

```bash
# Apply all pending migrations
make migrate
 
# Create a new migration from model changes
make migration MSG="describe_your_change"
 
# Roll back one step
make downgrade REV=-1
```

---

## Testing

The project has two test suites: unit tests (no external dependencies) and integration tests (in-process SQLite
database + HTTPX `TestClient`).

```bash
# Run only unit tests
make test-unit
 
# Run only integration tests
make test-integration
 
# Run everything with coverage
make test
```

Coverage is reported on every run with `pytest-cov`.

### Test Design

- **Unit tests** use hand-written repository fakes and a fake file storage implementation. Services are tested in
  isolation with no database or network calls.
- **Integration tests** spin up a real SQLite database with all Alembic migrations applied, wire up the full Dishka
  container, and make HTTP requests through the FastAPI TestClient.
- Test fixtures for JWT include real RSA keys so the full token signing/verification cycle runs in tests.

---

## CI/CD

### CI Pipeline (`.github/workflows/ci.yml`)

Triggered on pushes to `develop` / `main` and pull requests to `main`:

1. **pre-commit job:** runs Ruff (lint + format), ty (type checking), and tach (architecture boundaries) against all
   files
2. **unit-tests job:** runs the unit test suite
3. **integration-tests job:** runs on pull requests to `main` and on `main` branch pushes

All jobs use `uv` for fast, reproducible dependency installation with a cache layer.

### Release Pipeline (`.github/workflows/release.yml`)

Triggered automatically after CI passes on `main` (and manually via `workflow_dispatch`):

1. **publish:** builds a Docker image, tags it with the git SHA, and pushes it to GHCR (
   `ghcr.io/<owner>/<repo>:sha-<sha>`)
2. **deploy:** authenticates to AWS via OIDC (no stored secrets), queries CloudFormation stack outputs for the DB host
   and S3 bucket names, assembles a deployment bundle (compose file + deploy script + release env), uploads the bundle
   to S3, and triggers the deployment on EC2 via AWS SSM `send-command`. The workflow waits for the health check to pass
   before reporting success.

---

## AWS Deployment

The application features a fully automated, cloud-native deployment pipeline targeting **Amazon Web Services (AWS)**. It
uses **Infrastructure as Code (IaC)** to guarantee reproducible and scalable environments.

### Infrastructure as Code (CloudFormation)

The entire production infrastructure is defined in infrastructure/template.yaml. Deploying this template automatically
provisions:

- **Networking:** A custom VPC, Internet Gateway, and Public/Private Subnets.
- **Compute:** An EC2 Instance managed by an Auto Scaling Group (ASG) and initialized via a Launch Template.
- **Database:** A fully managed Amazon RDS PostgreSQL instance deployed in a private subnet, accessible only by the EC2
  backend.
- **Storage:** Two Amazon S3 Buckets - one for storing user documents securely, and one for storing deployment
  artifacts.
- **Security:** IAM Roles, Security Groups (Firewalls), and Instance Profiles.

To provision the infrastructure for the first time:

```bash
aws cloudformation deploy \
  --template-file infrastructure/template.yaml \
  --stack-name <your-stack-name> \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --profile <user_name> \
  --region <your_region>
```

The CloudFormation stack name is stored in the GitHub repository variable `STACK_NAME`. This is the only infrastructure
identifier kept in the repository. All sensitive values are kept outside the repository.

### Secrets Management

Production secrets are stored in **AWS Systems Manager Parameter Store** and fetched by the deploy script (
`infrastructure/deploy.sh`) at deploy time:

| Parameter           | Description                                    |
|---------------------|------------------------------------------------|
| `/prod/db/password` | Database password (SecureString)               |
| `/prod/jwt/private` | RSA private key for JWT signing (SecureString) |
| `/prod/jwt/public`  | RSA public key for JWT verification            |

The deploy script writes these values to the EC2 instance at deploy time and never commits them to version control or
passes them through environment variables in CI.

### Manual Deployment

To deploy a specific release manually, trigger the Release workflow via `workflow_dispatch` in GitHub Actions.

---

## Project Structure

```
flow/
├── app/
│   ├── api/v1/
│   │   ├── routes/          # FastAPI routers (auth, users, admin, projects, documents)
│   │   ├── exc_handler.py   # Global exception → HTTP response mapping
│   │   └── get_current_user.py  # JWT bearer token dependency
│   ├── core/
│   │   └── config.py        # Pydantic Settings (env-driven configuration)
│   ├── db/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   └── repositories/    # Concrete SQLAlchemy repository implementations
│   ├── domain/
│   │   ├── repositories/    # Abstract repository interfaces
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── mappers/         # ORM model → domain schema mappers
│   │   └── storage/         # Abstract file storage interface
│   ├── infrastructure/
│   │   └── s3_file_storage.py  # Concrete S3 storage adapter (aioboto3)
│   ├── providers/           # Dishka DI providers (db, repos, services, storage, config)
│   ├── services/            # Business logic services
│   └── main.py              # FastAPI application factory
├── alembic/                 # Migration scripts and Alembic env
├── infrastructure/
│   ├── template.yaml        # CloudFormation stack definition
│   └── deploy.sh            # EC2 deployment script (fetches secrets from SSM)
├── tests/
│   ├── unit/                # Unit tests with repository fakes
│   └── integration/         # Integration tests with SQLite + TestClient
├── .github/workflows/
│   ├── ci.yml               # Pre-commit, unit tests, integration tests
│   └── release.yml          # Docker image publish + EC2 deploy via SSM
├── docker-compose.yml       # Local stack (app + Postgres + pgAdmin)
├── docker-compose.prod.yml  # Production-oriented compose (app only)
├── Dockerfile               # Multi-stage build (builder + slim runtime)
├── pyproject.toml           # Project metadata and dependencies
├── ruff.toml                # Linter / formatter configuration
└── tach.toml                # Architecture boundary rules
```

---

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for the full text.
