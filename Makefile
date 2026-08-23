.PHONY: help validate test build check preview research-fixture clean

help:
	@printf '%s\n' \
	  'make validate          Validate catalog invariants' \
	  'make test              Run all deterministic tests and site checks' \
	  'make build             Generate the static site into dist/' \
	  'make preview           Serve dist/ at http://localhost:8000' \
	  'make research-fixture  Exercise the weekly pipeline without network/API access' \
	  'make clean             Remove generated output and Python caches'

validate:
	python3 scripts/validate.py

build: validate
	python3 scripts/build.py

check: build
	python3 scripts/check_site.py
	node --check site/app.js
	node --check site/theme.js
	node --check site/recommendation-engine.js
	node --check site/recommend.js
	node tests/recommendation-engine.test.js

test:
	python3 -m compileall -q scripts tests
	python3 -m unittest discover -s tests -v
	$(MAKE) check

preview: build
	python3 -m http.server 8000 --directory dist

research-fixture:
	@tmp="$$(mktemp -d)"; \
	python3 scripts/research.py --date 2026-08-23 --fixture tests/fixtures/research-output.json --output "$$tmp/proposal.json"; \
	python3 scripts/apply_proposal.py "$$tmp/proposal.json" --catalog catalog/providers.json --output "$$tmp/providers.json" --report "$$tmp/report.json"; \
	python3 scripts/proposal_markdown.py "$$tmp/proposal.json" --report "$$tmp/report.json" --output "$$tmp/review.md"; \
	echo "Fixture pipeline passed in $$tmp"; \
	rm -rf "$$tmp"

clean:
	rm -rf dist scripts/__pycache__ tests/__pycache__
