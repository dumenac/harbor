# Harbor — make targets
#   make check     lint everything and validate both appearances (what CI runs)
#   make install   ./install.sh          make link   ./install.sh --link
#   make keys      regenerate docs/keybindings.md from the i3 config
SHELL_SCRIPTS := install.sh uninstall.sh extras/*.sh config/i3/scripts/*.sh config/i3/scripts/launcher
PY_SCRIPTS    := config/i3/scripts/harbor config/i3/scripts/bar.py config/i3/scripts/keys.py \
                 config/i3/scripts/emoji.py config/i3/scripts/clipboard.py

.PHONY: check lint install link keys

check: lint
	@./tests/render-check.sh

lint:
	shellcheck $(SHELL_SCRIPTS)
	python3 -m py_compile $(PY_SCRIPTS)
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "✓ lint"

install:
	./install.sh

link:
	./install.sh --link

keys:
	@./tests/keys-markdown.sh > docs/keybindings.md
	@echo "✓ docs/keybindings.md"
