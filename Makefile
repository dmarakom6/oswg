.PHONY: build dev install lint clean rebuild help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## Build UI + copy static assets
	cd ui && npm run build
	rm -rf src/oswg/static
	cp -r ui/build src/oswg/static

dev: ## Build UI + start local web server
	$(MAKE) build
	python -m oswg ui

install: ## Install package in editable mode
	pip install -e '.[dev]'

lint: ## Run ruff + svelte-check
	ruff check src/
	cd ui && npx svelte-check

clean: ## Remove build artifacts
	rm -rf src/oswg/static ui/build ui/.svelte-kit dist build *.egg-info .pytest_cache .ruff_cache

rebuild: clean install build ## Full rebuild (clean + install + build)
