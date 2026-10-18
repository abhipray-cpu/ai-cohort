.PHONY: catalogbridge-build catalogbridge-up catalogbridge-down catalogbridge-status catalogbridge-test catalogbridge-validate catalogbridge-acceptance

catalogbridge-build:
	npm --prefix apps/catalogbridge-web run build

catalogbridge-up: catalogbridge-build
	$(PYTHON) scripts/dev_stack.py --product catalogbridge up

catalogbridge-down:
	$(PYTHON) scripts/dev_stack.py --product catalogbridge down

catalogbridge-status:
	$(PYTHON) scripts/dev_stack.py --product catalogbridge status

catalogbridge-test: catalogbridge-build
	$(PYTHON) -m pytest tests/test_catalogbridge*.py -q
	npm --prefix apps/catalogbridge-web test

# Validation is explicit and bounded; use --live only when service usage is authorized.
catalogbridge-validate:
	$(PYTHON) scripts/validate_catalogbridge.py $(CATALOGBRIDGE_VALIDATION_ARGS)

catalogbridge-acceptance:
	$(PYTHON) scripts/accept_catalogbridge.py

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

.PHONY: relaydesk-build relaydesk-up relaydesk-down relaydesk-status relaydesk-test relaydesk-model

relaydesk-build:
	npm --prefix apps/relaydesk-web run build

relaydesk-up: relaydesk-build
	$(PYTHON) scripts/dev_stack.py --product relaydesk up

relaydesk-down:
	$(PYTHON) scripts/dev_stack.py --product relaydesk down

relaydesk-status:
	$(PYTHON) scripts/dev_stack.py --product relaydesk status

relaydesk-model:
	$(PYTHON) scripts/provision_relaydesk_model.py

relaydesk-test: relaydesk-build
	$(PYTHON) -m pytest tests/test_relaydesk*.py -q
	npm --prefix apps/relaydesk-web test

.PHONY: relaydesk-acceptance
ACCEPTANCE_OUTPUT ?= var/validation/relaydesk-acceptance
ACCEPTANCE_AUDIT ?= var/validation/relaydesk-corrective-audit-v3.json

# Intentionally nonzero until every mandatory gate has real passing evidence.
# Use a new output path for each run; never overwrite failed acceptance artifacts.
relaydesk-acceptance:
	$(PYTHON) scripts/accept_relaydesk.py --output "$(ACCEPTANCE_OUTPUT)" --audit "$(ACCEPTANCE_AUDIT)" --run-tests

.PHONY: clausegate-build clausegate-up clausegate-down clausegate-status clausegate-test clausegate-capture clausegate-validate clausegate-acceptance
CLAUSEGATE_CORPUS ?= var/validation/clausegate-corpus-v2
CLAUSEGATE_OUTPUT ?= var/validation/clausegate-validation

clausegate-build:
	npm --prefix apps/clausegate-web run build

clausegate-up: clausegate-build
	$(PYTHON) scripts/dev_stack.py --product clausegate up

clausegate-down:
	$(PYTHON) scripts/dev_stack.py --product clausegate down

clausegate-status:
	$(PYTHON) scripts/dev_stack.py --product clausegate status

clausegate-test: clausegate-build
	$(PYTHON) -m pytest tests/test_clausegate*.py -q
	npm --prefix apps/clausegate-web test

clausegate-capture:
	$(PYTHON) scripts/capture_clausegate_corpus.py --output "$(CLAUSEGATE_CORPUS)"

clausegate-validate:
	$(PYTHON) scripts/validate_clausegate.py --corpus "$(CLAUSEGATE_CORPUS)" --output "$(CLAUSEGATE_OUTPUT)"

clausegate-acceptance:
	$(PYTHON) scripts/accept_clausegate.py --evidence "$(CLAUSEGATE_OUTPUT)/report.json" --output "$(CLAUSEGATE_OUTPUT)/acceptance" --run-tests
