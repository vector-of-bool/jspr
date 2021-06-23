.SILENT:
.PHONY: docs poetry-install _poetry-update

# Re-generate poetry.lock if the project file changes
poetry.lock: pyproject.toml
	poetry lock

poetry-lock: poetry.lock

# Run 'poetry install' if the lockfile changes
_build/.poetry-installed: poetry.lock
	poetry install
	touch _build/.poetry-installed

poetry-install: _build/.poetry-installed

docs: poetry-install
	echo Building docs...
	poetry run sphinx-build -aqWj8 -b html docs/ _build/docs/

test: poetry-install
	echo Executing pytest...
	poetry run pytest
