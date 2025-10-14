.PHONY: help build prepare train evaluate predict interactive all clean

help:
	@echo "Available commands:"
	@echo "  make build        - Build Docker container"
	@echo "  make prepare      - Run feature preparation"
	@echo "  make train        - Train model"
	@echo "  make evaluate     - Evaluate model"
	@echo "  make predict      - Generate 2025 predictions"
	@echo "  make interactive  - Run interactive forecasting"
	@echo "  make all          - Run full pipeline"
	@echo "  make clean        - Remove Docker images"

build:
	docker-compose build

prepare:
	docker-compose run --rm yield-forecasting python scripts/1_prepare_features.py

train:
	docker-compose run --rm yield-forecasting python scripts/2_train_models.py

evaluate:
	docker-compose run --rm yield-forecasting python scripts/3_evaluate_models.py

predict:
	docker-compose run --rm yield-forecasting python scripts/4_predict_current_year.py

interactive:
	docker-compose run --rm yield-forecasting python scripts/interactive_forecast.py

all:
	docker-compose run --rm yield-forecasting bash -c "\
		python scripts/1_prepare_features.py && \
		python scripts/2_train_models.py && \
		python scripts/3_evaluate_models.py && \
		python scripts/4_predict_current_year.py"

clean:
	docker-compose down
	docker rmi yield-forecasting