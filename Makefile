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
	@echo "  make run        - Запуск app.py"
	@echo "  make dev        - Запуск в dev режимі"
	@echo ""

# Встановити залежності
install:
	pip install -r requirements.txt
	pip install pytest pytest-cov black isort flake8

# Запустити тести
test:
	PYTHONPATH=. python3 -m pytest tests/ -v

# Тести з coverage (потрібен pytest та pytest-cov)
test-cov:
	python3 -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html:coverage_html --cov-fail-under=0 2>/dev/null || $(MAKE) test
	@echo "Coverage: coverage_html/index.html"

# Швидкі тести
test-fast:
	$(MAKE) test

# Перевірка коду
lint:
	@echo "=== Ruff/Lint ==="
	ruff check . --ignore E501 2>/dev/null || true
	@echo ""
	@echo "=== Black check ==="
	black --check --diff *.py tests/ 2>/dev/null || true

# Форматування коду
format:
	black *.py tests/ 2>/dev/null || true
	isort *.py tests/ 2>/dev/null || true

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
	python3 app.py

# Запуск dev режим
dev:
	FLASK_ENV=development FLASK_DEBUG=1 python3 app.py

# Перевірка типів (якщо є mypy)
typecheck:
	mypy app.py --ignore-missing-imports || true

# Показати статистику коду
stats:
	@echo "=== Рядків коду ==="
	@find . -path ./static -prune -o -path ./.git -prune -o -name "*.py" -print | xargs cat 2>/dev/null | wc -l
	@echo "=== Тестів ==="
	@PYTHONPATH=. python3 -m pytest tests/ -q 2>/dev/null || true

# Docker build
docker-build:
	docker build -t neptun:latest .

# Docker run
docker-run:
	docker run -p 5000:5000 --env-file .env neptun:latest
