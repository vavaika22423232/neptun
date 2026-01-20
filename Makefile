# Neptun 2.0 Makefile
# Команди для розробки та тестування

.PHONY: help test test-cov lint format clean run dev install

# Default target
help:
	@echo "Neptun 2.0 - Команди:"
	@echo ""
	@echo "  make install    - Встановити залежності"
	@echo "  make test       - Запустити тести"
	@echo "  make test-cov   - Тести з coverage"
	@echo "  make lint       - Перевірка коду"
	@echo "  make format     - Форматування коду"
	@echo "  make clean      - Очистити кеш"
	@echo "  make run        - Запуск app_new.py"
	@echo "  make dev        - Запуск в dev режимі"
	@echo ""

# Встановити залежності
install:
	pip install -r requirements.txt
	pip install pytest pytest-cov black isort flake8

# Запустити тести
test:
	python3 -m pytest tests/ -v --tb=short

# Тести з coverage
test-cov:
	python3 -m pytest tests/ -v \
		--cov=services \
		--cov=api \
		--cov=utils \
		--cov=domain \
		--cov-report=term-missing \
		--cov-report=html:coverage_html
	@echo ""
	@echo "Coverage report: coverage_html/index.html"

# Швидкі тести (без інтеграційних)
test-fast:
	python3 -m pytest tests/ -v --ignore=tests/test_integration.py -x

# Перевірка коду
lint:
	@echo "=== Flake8 ==="
	flake8 services/ api/ utils/ domain/ --max-line-length=120 --ignore=E501,W503,E402 || true
	@echo ""
	@echo "=== Black check ==="
	black --check --diff services/ api/ utils/ domain/ 2>/dev/null || true
	@echo ""
	@echo "=== isort check ==="
	isort --check-only --diff services/ api/ utils/ domain/ 2>/dev/null || true

# Форматування коду
format:
	black services/ api/ utils/ domain/ tests/
	isort services/ api/ utils/ domain/ tests/

# Очистити кеш
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf coverage_html/ .coverage coverage.xml 2>/dev/null || true
	@echo "Cleaned!"

# Запуск продакшн
run:
	python3 app_new.py

# Запуск dev режим
dev:
	FLASK_ENV=development FLASK_DEBUG=1 python3 app_new.py

# Перевірка типів (якщо є mypy)
typecheck:
	mypy services/ api/ utils/ domain/ --ignore-missing-imports || true

# Показати статистику коду
stats:
	@echo "=== Рядків коду ==="
	@find services api utils domain -name "*.py" -exec cat {} + | wc -l
	@echo ""
	@echo "=== Файлів ==="
	@find services api utils domain -name "*.py" | wc -l
	@echo ""
	@echo "=== Тестів ==="
	@python3 -m pytest tests/ --collect-only -q 2>/dev/null | tail -1

# Docker build
docker-build:
	docker build -t neptun:latest .

# Docker run
docker-run:
	docker run -p 5000:5000 --env-file .env neptun:latest
