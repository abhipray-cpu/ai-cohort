ifeq ($(OS),Windows_NT)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= .venv/bin/python
endif

.PHONY: up down status web-build

web-build:
	npm --prefix apps/tenderlens-web run build

up: web-build
	$(PYTHON) scripts/dev_stack.py up

down:
	$(PYTHON) scripts/dev_stack.py down

status:
	$(PYTHON) scripts/dev_stack.py status
