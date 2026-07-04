.PHONY: dev test ingest seed eval run-db clean

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --ignore=tests/test_api.py

ingest:
	python scripts/ingest_pdfs.py

seed:
	python scripts/seed_partners.py

eval:
	python scripts/run_evaluation.py

run-db:
	docker compose up -d qdrant redis postgres

run-all:
	docker compose --profile monitoring up -d

metrics:
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana:    http://localhost:3000"
	@echo "Metrics:    http://localhost:8000/metrics"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; \
	rm -rf .pytest_cache 2>/dev/null; true
