.PHONY: run smoke help

help:
	@echo "Targets:"
	@echo "  make run    - build all images and run full pipeline (ingest -> preprocess -> stress -> yield)"
	@echo "  make smoke  - build images and run the workflow container (sample end-to-end)"

run:
	docker compose build
	docker compose run --rm data-ingestion \
		python src/download_yield_data.py --start-year 2015 --end-year 2024 --sample
	docker compose run --rm data-preprocessing \
		python src/preprocess_data.py
	docker compose run --rm model-stress-detection \
		python src/train_model.py --verbose
	docker compose run --rm model-yield-forecasting \
		python src/train_model.py --verbose

smoke:
	docker compose build
	docker compose run --rm workflow \
		python run_workflow.py --start-year 2015 --end-year 2024 --sample
