set fallback := true
# Root justfile for Opencode Plugins

plugins := "opencode-plugin-improved-task opencode-plugin-improved-todowrite opencode-plugin-improved-webtools opencode-plugin-mcp-shim opencode-manager opencode-postgres-memory-plugin opencode-time-travel-plugin opencode-zotero-plugin opencode-plugin-prompt-transformer opencode-plugin-reminder-injection"

# Synchronize package.json repository URLs with actual git remotes
sync-all-metadata:
	#!/usr/bin/env bash
	set -euo pipefail
	for plugin in {{plugins}}; do
		if [ -f "$plugin/package.json" ]; then
			echo "Syncing $plugin"
			REPO_URL=$(cd "$plugin" && git remote get-url origin | sed 's/git@github.com:/https:\/\/github.com\//')
			python3 -c "import json; d=json.load(open('$plugin/package.json')); d['repository']={'type':'git','url':'git+'+'$REPO_URL'}; json.dump(d, open('$plugin/package.json','w'), indent=2); print('', file=open('$plugin/package.json','a'))"
		fi
	done

# Setup npm trusted publisher for ALL plugins
setup-all-npm-trust:
	#!/usr/bin/env bash
	for plugin in {{plugins}}; do
		echo "Trusting $plugin"
		just --justfile "$plugin/justfile" --working-directory "$plugin" setup-npm-trust
	done

# Initial publish for ALL plugins
publish-all:
	#!/usr/bin/env bash
	for plugin in {{plugins}}; do
		echo "Publishing $plugin"
		just --justfile "$plugin/justfile" --working-directory "$plugin" publish
	done

# Run typecheck for all plugins
check-all:
	#!/usr/bin/env bash
	for plugin in {{plugins}}; do
		if grep -q "typecheck:" "$plugin/justfile"; then
			echo "Typechecking $plugin"
			just --justfile "$plugin/justfile" --working-directory "$plugin" typecheck
		fi
	done

# Dashboard recipes
check-dashboard:
	@bunx tsc dashboard.ts --noEmit --esModuleInterop --skipLibCheck --target esnext --lib esnext,dom

build-dashboard: check-dashboard
	@bunx tsc dashboard.ts --outFile /home/dzack/www/html/dashboard.js --esModuleInterop --skipLibCheck --target esnext --lib esnext,dom

refresh-dashboard-token:
	@python3 -c "import subprocess; token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip(); open('/home/dzack/www/html/config.js', 'w').write(f'window.GITHUB_TOKEN = \"{token}\";\n')"

update-usage:
        #!/usr/bin/env bash
        set -euo pipefail
        source ~/.envrc 2>/dev/null || true
        uvx --from git+https://github.com/dzackgarza/usage-limits usage-limits --json > /home/dzack/www/html/usage.json

# ---------------------------------------------------------------------------
# Isolated Test Sandbox
# ---------------------------------------------------------------------------
#
# Two recipes: test-sandbox-up and test-sandbox-down.
#
# All sandbox paths are fixed constants defined in .testrc (the single source
# of truth for test env vars). Both recipes source .testrc to get those paths.
#
# test-sandbox-up:
#   1. Sources .testrc for fixed sandbox paths.
#   2. Tears down any existing sandbox at the fixed path.
#   3. Creates the dir structure.
#   4. Copies .testrc into $OPENCODE_TEST_SANDBOX/home/.envrc (direnv allow).
#   5. Copies the plugin .envrc into $OPENCODE_TEST_PROJECT_DIR/.envrc (direnv allow).
#      That .envrc must use source_up to inherit .testrc vars; it works because
#      OPENCODE_TEST_PROJECT_DIR lives inside the sandbox HOME.
#   6. Copies global opencode.json and auth.json from the real user HOME.
#   7. Copies the per-plugin opencode.json into the project dir.
#   8. Starts the server: env -i + direnv exec so the process sees only .testrc vars.
#
# Plugin justfiles call:
#   just -f "$root_justfile" test-sandbox-up config=".../opencode.json" envrc=".../plugin.envrc"
#   direnv exec "{{repo_root}}" bun test tests/integration
#
# No .test-sandbox-env.sh, no .test-sandbox-path, no .test-server.pid.

test_port := "4097"
test_host := "127.0.0.1"
test_base_url := "http://" + test_host + ":" + test_port

# Stand up an isolated OpenCode test sandbox on 127.0.0.1:4097.
# Requires:
#   config — absolute path to plugin's tests/integration/opencode.json
#   envrc  — absolute path to plugin's .envrc (must use source_up)
[group('test')]
test-sandbox-up config envrc:
	#!/usr/bin/env bash
	set -euo pipefail

	# Capture real HOME/XDG before .testrc overwrites them.
	# Needed to copy global config and auth.json from the actual user home.
	REAL_HOME="$HOME"
	REAL_XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

	# Source .testrc — defines all fixed sandbox paths.
	# After this point HOME = $OPENCODE_TEST_SANDBOX/home (the sandbox HOME).
	source "{{justfile_directory()}}/.testrc"

	# Tear down any existing sandbox at the fixed path.
	if [[ -f "$OPENCODE_TEST_SANDBOX/.pid" ]]; then
	  pid=$(cat "$OPENCODE_TEST_SANDBOX/.pid")
	  if kill -0 "$pid" 2>/dev/null; then
	    echo "Tearing down existing sandbox (pid $pid)" >&2
	    kill "$pid" 2>/dev/null || true
	    sleep 0.5
	  fi
	fi
	rm -rf "$OPENCODE_TEST_SANDBOX"
	rm -f "{{justfile_directory()}}/.test-sandbox-path" \
	      "{{justfile_directory()}}/.test-server.pid" \
	      "{{justfile_directory()}}/.test-sandbox-env.sh"

	# Create dir structure. All paths come from .testrc.
	mkdir -p \
	  "$XDG_CONFIG_HOME/opencode" \
	  "$XDG_CACHE_HOME" \
	  "$XDG_STATE_HOME" \
	  "$XDG_DATA_HOME/opencode" \
	  "$HOME" \
	  "$OPENCODE_TEST_PROJECT_DIR"

	# .testrc is the single source of truth for test env vars.
	# Copy it into sandbox HOME as .envrc so direnv exec loads it for the server.
	cp "{{justfile_directory()}}/.testrc" "$HOME/.envrc"
	direnv allow "$HOME/.envrc"

	# Copy plugin .envrc into project dir. It must use source_up so direnv's
	# traversal finds $HOME/.envrc (= .testrc copy) since OPENCODE_TEST_PROJECT_DIR
	# lives inside the sandbox HOME.
	cp "{{envrc}}" "$OPENCODE_TEST_PROJECT_DIR/.envrc"
	direnv allow "$OPENCODE_TEST_PROJECT_DIR/.envrc"

	# Copy global opencode config and auth.json from real HOME into sandbox.
	# These provide provider auth without leaking other shell vars.
	real_global_config="$REAL_HOME/.config/opencode/opencode.json"
	if [[ -f "$real_global_config" ]]; then
	  cp "$real_global_config" "$XDG_CONFIG_HOME/opencode/opencode.json"
	fi
	real_auth_json="$REAL_XDG_DATA_HOME/opencode/auth.json"
	if [[ -f "$real_auth_json" ]]; then
	  cp "$real_auth_json" "$XDG_DATA_HOME/opencode/auth.json"
	fi

	# Copy per-plugin opencode.json into project dir.
	# OpenCode merges this on top of the global config (plugin, agent permission overrides).
	cp "{{config}}" "$OPENCODE_TEST_PROJECT_DIR/opencode.json"

	# Start server with a clean environment.
	# env -i clears all inherited vars (no GITHUB_TOKEN PAT leakage, no stray secrets).
	# direnv exec loads only what's defined in the .testrc chain via source_up.
	env -i \
	  HOME="$HOME" \
	  PATH="$PATH" \
	  direnv exec "$OPENCODE_TEST_PROJECT_DIR" \
	  bash -c "opencode serve --hostname '{{test_host}}' --port '{{test_port}}' --print-logs --log-level INFO" \
	  > "$OPENCODE_TEST_SANDBOX/server.log" 2>&1 &
	server_pid=$!

	# Record PID in sandbox — teardown reads it from here.
	echo "$server_pid" > "$OPENCODE_TEST_SANDBOX/.pid"

	# Health check: poll /global/health for up to 60s.
	deadline=$((SECONDS + 60))
	while (( SECONDS < deadline )); do
	  if ! kill -0 "$server_pid" 2>/dev/null; then
	    echo "Server exited early (pid $server_pid). Logs:" >&2
	    tail -30 "$OPENCODE_TEST_SANDBOX/server.log" >&2
	    rm -rf "$OPENCODE_TEST_SANDBOX"
	    exit 1
	  fi
	  if curl -sf "{{test_base_url}}/global/health" >/dev/null 2>&1; then
	    echo "Sandbox ready at {{test_base_url}} (pid $server_pid)"
	    exit 0
	  fi
	  sleep 0.3
	done

	echo "Timed out waiting for server health check. Logs:" >&2
	tail -30 "$OPENCODE_TEST_SANDBOX/server.log" >&2
	kill "$server_pid" 2>/dev/null || true
	rm -rf "$OPENCODE_TEST_SANDBOX"
	exit 1

# Tear down the test sandbox: kill server and remove the fixed sandbox dir.
[group('test')]
test-sandbox-down:
	#!/usr/bin/env bash
	set -euo pipefail
	source "{{justfile_directory()}}/.testrc"

	if [[ ! -d "$OPENCODE_TEST_SANDBOX" ]]; then
	  echo "No sandbox found at $OPENCODE_TEST_SANDBOX" >&2
	  exit 0
	fi

	if [[ -f "$OPENCODE_TEST_SANDBOX/.pid" ]]; then
	  pid=$(cat "$OPENCODE_TEST_SANDBOX/.pid")
	  if kill -0 "$pid" 2>/dev/null; then
	    kill "$pid"
	    for i in $(seq 1 50); do
	      kill -0 "$pid" 2>/dev/null || break
	      sleep 0.1
	    done
	    kill -9 "$pid" 2>/dev/null || true
	  fi
	fi

	rm -rf "$OPENCODE_TEST_SANDBOX"
	# Clean up any legacy artifacts from previous sandbox architecture.
	rm -f "{{justfile_directory()}}/.test-sandbox-path" \
	      "{{justfile_directory()}}/.test-server.pid" \
	      "{{justfile_directory()}}/.test-sandbox-env.sh"
	echo "Sandbox torn down."

# ---------------------------------------------------------------------------
# Ctags
# ---------------------------------------------------------------------------

# Regenerate ctags for a directory with proper process management
# Uses flock to prevent concurrent runs, timeout to kill hung processes
# Only indexes source code (no docs), outputs to tags in project root
ctags dir=".":
	#!/usr/bin/env bash
	set -euo pipefail
	LOCKFILE="{{dir}}/.git/ctags.lock"
	TIMEOUT_SECONDS=60
	TAGS_FILE="{{dir}}/tags"
	flock -n -x "$LOCKFILE" timeout "$TIMEOUT_SECONDS" ctags -R \
		--extras=+r \
		--tag-relative=yes \
		--languages=JavaScript,TypeScript,Python,Rust,Go,Java,C,C++,Markdown \
		--exclude=.git \
		--exclude=node_modules \
		--exclude=vendor \
		--exclude=dist \
		--exclude=build \
		--exclude=.venv \
		--exclude=__pycache__ \
		--exclude='**/*.min.js' \
		--exclude='**/*.bundle.js' \
		--exclude='**/*.d.ts' \
		--exclude='**/shims/**' \
		-f "$TAGS_FILE" \
		"{{dir}}" >/dev/null 2>&1 || true
