PY = python3
SRC_DIR = src
BUILD_DIR = dist
STAGING = .build
ENTRY = entry:main
OUT = $(BUILD_DIR)/nscb.pyz

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +; \
	rm -rf \
		$(STAGING) \
		$(BUILD_DIR) \
		.pytest_cache \
		.ruff_cache \
		.coverage

build: clean
	mkdir -p $(BUILD_DIR)
	rm -rf $(STAGING)
	mkdir -p $(STAGING)
	# Copy contents of src to staging root so nscb is at top level
	cp -r $(SRC_DIR)/nscb $(STAGING)/
	cp $(SRC_DIR)/entry.py $(STAGING)/
	$(PY) -m zipapp $(STAGING) -o $(OUT) -m $(ENTRY) -p "/usr/bin/env python3"
	chmod +x $(OUT)

install: $(OUT)
	@if [ -d "$$HOME/.local/bin/scripts/" ]; then \
		INSTALL_DIR="$$HOME/.local/bin/scripts"; \
	else \
		mkdir -p "$$HOME/.local/bin"; \
		INSTALL_DIR="$$HOME/.local/bin"; \
	fi; \
	cp $(OUT) "$$INSTALL_DIR/nscb.pyz"; \
	chmod +x "$$INSTALL_DIR/nscb.pyz"; \
	ln -sf "$$INSTALL_DIR/nscb.pyz" "$$HOME/.local/bin/nscb"; \
	echo "Installed to $$INSTALL_DIR/nscb.pyz"

test:
	uv run pytest -xvs --cov=src --cov-report=term-missing

radon:
	uv run radon cc ./src -a

quality:
	ruff check --select I --fix ./src ./tests; \
		ruff format ./src ./tests; \
		pyright ./src ./tests

all: clean build install

.PHONY: all clean install
