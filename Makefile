.PHONY: run precommit test check migrate migration downgrade

REV ?= head
MSG ?= empty message

run:
	uv run uvicorn app.main:create_app --factory --reload

precommit:
	uv run pre-commit run --all-files

test:
	uv run pytest -svv --cov=app --cov-report=term-missing

check: precommit test

migration:
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate:
	uv run alembic upgrade $(REV)

downgrade:
	uv run alembic downgrade $(REV)