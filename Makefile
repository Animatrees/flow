.PHONY: run precommit test check

run:
	uv run uvicorn main:app --reload

precommit:
	uv run pre-commit run --all-files

test:
	uv run pytest -svv

check: precommit test
