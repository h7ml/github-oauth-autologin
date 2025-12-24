.PHONY: help install test lint format type-check clean run docs

help:  ## 显示帮助信息
	@echo "HaloLight Athena - Makefile 命令"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	pip install -r requirements.txt
	playwright install chromium

test:  ## 运行测试
	pytest -v

test-cov:  ## 运行测试并生成覆盖率报告
	pytest --cov=core --cov=utils --cov=sites --cov=notifiers --cov-report=html --cov-report=term-missing
	@echo "覆盖率报告已生成: htmlcov/index.html"

lint:  ## 运行 Pylint 检查
	pylint core/ utils/ sites/ notifiers/

format:  ## 格式化代码（Black）
	black core/ utils/ sites/ notifiers/ tests/

format-check:  ## 检查代码格式
	black --check core/ utils/ sites/ notifiers/ tests/

type-check:  ## 运行类型检查（Mypy）
	mypy core/ utils/

clean:  ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov .tox
	rm -f *.png *.log .athena_state.json

run:  ## 运行主程序（需要指定站点，如: make run SITE=clawcloud）
	@if [ -z "$(SITE)" ]; then \
		echo "错误: 请指定站点，例如: make run SITE=clawcloud"; \
		exit 1; \
	fi
	python main.py $(SITE)

run-login-only:  ## 运行仅登录模式
	python login_only.py

docs:  ## 在浏览器中打开文档
	@if command -v open > /dev/null; then \
		open docs/index.html; \
	elif command -v xdg-open > /dev/null; then \
		xdg-open docs/index.html; \
	else \
		echo "请手动打开: docs/index.html"; \
	fi

all: format lint type-check test  ## 运行所有检查

ci: format-check lint type-check test-cov  ## CI 流水线检查

