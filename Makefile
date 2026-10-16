ifeq ($(OS),Windows_NT)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= .venv/bin/python
endif

.PHONY: up down status web-build resolvedesk-up resolvedesk-down resolvedesk-status resolvedesk-build resolvedesk-test resolvedesk-validate-live

web-build:
	npm --prefix apps/tenderlens-web run build

up: web-build
	$(PYTHON) scripts/dev_stack.py up

down:
	$(PYTHON) scripts/dev_stack.py down

status:
	$(PYTHON) scripts/dev_stack.py status

resolvedesk-build:
	npm --prefix apps/resolvedesk-web run build

resolvedesk-up: resolvedesk-build
	$(PYTHON) scripts/dev_stack.py --product resolvedesk up

resolvedesk-down:
	$(PYTHON) scripts/dev_stack.py --product resolvedesk down

resolvedesk-status:
	$(PYTHON) scripts/dev_stack.py --product resolvedesk status

resolvedesk-test: resolvedesk-build
	$(PYTHON) -m pytest tests/test_resolvedesk.py tests/test_resolvedesk_chat.py tests/test_resolvedesk_sources.py tests/test_resolvedesk_acceptance.py
	npm --prefix apps/resolvedesk-web test

# Explicitly invokes real Codex and official-source search; consumes service usage.
resolvedesk-validate-live:
	$(PYTHON) scripts/validate_resolvedesk_chat.py --live

.PHONY: propertybrief-build propertybrief-up propertybrief-down propertybrief-status propertybrief-test propertybrief-validate-live

propertybrief-build:
	npm --prefix apps/propertybrief-web run build

propertybrief-up: propertybrief-build
	$(PYTHON) scripts/dev_stack.py --product propertybrief up

propertybrief-down:
	$(PYTHON) scripts/dev_stack.py --product propertybrief down

propertybrief-status:
	$(PYTHON) scripts/dev_stack.py --product propertybrief status

propertybrief-test: propertybrief-build
	$(PYTHON) -m pytest tests/test_propertybrief*.py
	npm --prefix apps/propertybrief-web test

propertybrief-validate-live:
	$(PYTHON) scripts/validate_propertybrief.py --live

.PHONY: patchdesk-build patchdesk-up patchdesk-down patchdesk-status patchdesk-test patchdesk-validate-live

patchdesk-build:
	npm --prefix apps/patchdesk-web run build

patchdesk-up: patchdesk-build
	$(PYTHON) scripts/dev_stack.py --product patchdesk up

patchdesk-down:
	$(PYTHON) scripts/dev_stack.py --product patchdesk down

patchdesk-status:
	$(PYTHON) scripts/dev_stack.py --product patchdesk status

patchdesk-test: patchdesk-build
	$(PYTHON) -m pytest tests/test_patchdesk*.py -q
	npm --prefix apps/patchdesk-web test

patchdesk-validate-live:
	$(PYTHON) scripts/validate_patchdesk.py --live
