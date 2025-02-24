PYTHONPATH = PYTHONPATH=./
RUN = $(PYTHONPATH) poetry run
TEST = $(RUN) pytest $(arg)
POETRY_RUN = poetry run

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	poetry install --no-interaction --no-ansi --no-root --all-extras

.PHONY: format
format: ## Run linters in format mode
	$(POETRY_RUN) black ./src ./tests
	$(POETRY_RUN) ruff check --fix ./src ./tests
	$(POETRY_RUN) mypy ./src ./tests
	$(POETRY_RUN) pytest --dead-fixtures --dup-fixtures

.PHONY: lint
lint: ## Run linters in check mode
	$(POETRY_RUN) black --check ./src ./tests
	$(POETRY_RUN) ruff check ./src ./tests
	$(POETRY_RUN) mypy ./src ./tests
	$(POETRY_RUN) pytest --dead-fixtures --dup-fixtures

.PHONY: test
test: ## Runs pytest with coverage
	$(TEST) tests/ --cov=src --cov-report json --cov-report term --cov-report xml:cobertura.xml

.PHONY: sync
sync:
	git push --progress --porcelain task-1 refs/heads/master:master -f
	git push --progress --porcelain task-2 refs/heads/master:master -f
	git push --progress --porcelain task-3 refs/heads/master:master -f
	git push --progress --porcelain task-4 refs/heads/master:master -f
	git push --progress --porcelain task-5 refs/heads/master:master -f
