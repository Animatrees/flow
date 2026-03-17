.PHONY: run precommit test check

run:
	uv run uvicorn app.main:create_app --factory --reload

precommit:
	uv run pre-commit run --all-files

test:
	uv run pytest -svv --cov=app --cov-report=term-missing

check: precommit test
