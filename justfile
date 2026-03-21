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
# test-sandbox-up creates an entirely new tmp sandbox with its own HOME/XDG
# directories plus a dedicated project directory for package-specific test data.
# It starts a separate `opencode serve` instance on the canonical fixed test
# address, health-checks it, and writes PID/path/env metadata at the repo root.
#
# Config note: OpenCode resolves config by precedence; refer to the OpenCode
# docs when deciding whether a test needs only the copied global skeleton config
# or a package/project-specific override. If a package needs custom agents,
# plugin installation by file path/git, or stricter test-only permissions, pass
# explicit override files to this recipe so they are copied into the sandbox
# before the server starts.
#
# Usage:
#   just test-sandbox-up
#   TEST_SANDBOX_CONFIG_JSON=/abs/path/to/opencode.json just test-sandbox-up
#   source .test-sandbox-env.sh
#   OPENCODE_BASE_URL=http://127.0.0.1:4097 bun test
#   just test-sandbox-down

test_port := "4097"
test_host := "127.0.0.1"
test_base_url := "http://" + test_host + ":" + test_port
test_sandbox_env := justfile_directory() + "/.test-sandbox-env.sh"

# Stand up an isolated OpenCode test sandbox on 127.0.0.1:4097.
# This scaffolds a new tmp HOME/XDG tree plus a sandbox-local project dir and
# writes `.test-sandbox-env.sh` so package repos can source the exact runtime.
# Optional override files are copied into the sandbox before startup.
[group('test')]
test-sandbox-up config envrc:
	#!/usr/bin/env bash
	set -euo pipefail

	# Load test environment from the plugin's .envrc chain (includes .testrc).
	# Passphrases, agent names, and all test-specific vars must be defined there.
	eval "$(cd "$(dirname "{{envrc}}")" && direnv export bash 2>/dev/null)" || {
	  echo "error: failed to load env from {{envrc}} — run 'direnv allow' in that directory first" >&2
	  exit 1
	}

	# Tear down any existing sandbox before provisioning a new one
	if [[ -f "{{justfile_directory()}}/.test-sandbox-path" ]]; then
	  sandbox=$(cat "{{justfile_directory()}}/.test-sandbox-path")
	  if [[ -f "$sandbox/.pid" ]] && kill -0 "$(cat "$sandbox/.pid")" 2>/dev/null; then
	    echo "Tearing down existing sandbox (pid $(cat "$sandbox/.pid"), path $sandbox)" >&2
	    kill "$(cat "$sandbox/.pid")" 2>/dev/null || true
	    sleep 0.5
	  fi
	  rm -rf "$sandbox"
	  rm -f "{{justfile_directory()}}/.test-sandbox-path" "{{justfile_directory()}}/.test-server.pid" "{{test_sandbox_env}}"
	fi

	# Create isolated tmpdir
	sandbox=$(mktemp -d "/tmp/opencode-test-XXXXXXXXXX")
	config_home="$sandbox/config"
	cache_home="$sandbox/cache"
	state_home="$sandbox/state"
	data_home="$sandbox/data"
	fake_home="$sandbox/home"
	project_dir="$sandbox/project"
	mkdir -p "$config_home/opencode" "$cache_home" "$state_home" "$data_home" "$fake_home" "$project_dir"

	# Canonical test defaults. Override here only if the root workspace standard changes.
	export SERVER_URL="{{test_host}}"
	export SERVER_PORT="{{test_port}}"
	export OPENCODE_BASE_URL="{{test_base_url}}"
	export OPENCODE_DISABLE_CLAUDE_CODE="${OPENCODE_DISABLE_CLAUDE_CODE:-1}"
	export OPENCODE_ENABLE_EXA="${OPENCODE_ENABLE_EXA:-1}"
	export OPENCODE_EXPERIMENTAL_LSP_TY="${OPENCODE_EXPERIMENTAL_LSP_TY:-1}"
	export OPENCODE_EXPERIMENTAL_LSP_TOOL="${OPENCODE_EXPERIMENTAL_LSP_TOOL:-true}"

	# Copy the real global config and auth into the sandbox so provider auth is preserved.
	# Neither file is modified — they provide auth tokens, model defaults, and provider settings.
	global_config="$HOME/.config/opencode/opencode.json"
	if [[ -f "$global_config" ]]; then
	  cp "$global_config" "$config_home/opencode/opencode.json"
	fi
	auth_json="${XDG_DATA_HOME:-$HOME/.local/share}/opencode/auth.json"
	if [[ -f "$auth_json" ]]; then
	  mkdir -p "$data_home/opencode"
	  cp "$auth_json" "$data_home/opencode/auth.json"
	fi

	# Copy the per-test project config into the sandbox project dir.
	# OpenCode discovers this as a project-level config and merges it on top of the
	# global config — project settings (plugin, agent, model) override global defaults
	# while provider auth from the global config is preserved unchanged.
	cp "{{config}}" "$project_dir/opencode.json"

	cat > "{{test_sandbox_env}}" <<-EOF
	export HOME="$fake_home"
	export XDG_CONFIG_HOME="$config_home"
	export XDG_CACHE_HOME="$cache_home"
	export XDG_STATE_HOME="$state_home"
	export XDG_DATA_HOME="$data_home"
	export OPENCODE_BASE_URL="{{test_base_url}}"
	export OPENCODE_TEST_PROJECT_DIR="$project_dir"
	export SERVER_URL="{{test_host}}"
	export SERVER_PORT="{{test_port}}"
	export OPENCODE_DISABLE_CLAUDE_CODE="$OPENCODE_DISABLE_CLAUDE_CODE"
	export OPENCODE_ENABLE_EXA="$OPENCODE_ENABLE_EXA"
	export OPENCODE_EXPERIMENTAL_LSP_TY="$OPENCODE_EXPERIMENTAL_LSP_TY"
	export OPENCODE_EXPERIMENTAL_LSP_TOOL="$OPENCODE_EXPERIMENTAL_LSP_TOOL"
	EOF

	# Start server with a clean environment — no inherited shell vars, no leaked secrets.
	# Auth comes exclusively from the copied config and auth.json files above.
	# env -i clears the inherited env; PATH is passed explicitly so binaries resolve.
	env -i \
	  PATH="$PATH" \
	  HOME="$fake_home" \
	  XDG_CONFIG_HOME="$config_home" \
	  XDG_CACHE_HOME="$cache_home" \
	  XDG_STATE_HOME="$state_home" \
	  XDG_DATA_HOME="$data_home" \
	  OPENCODE_BASE_URL="{{test_base_url}}" \
	  OPENCODE_DISABLE_CLAUDE_CODE="${OPENCODE_DISABLE_CLAUDE_CODE:-1}" \
	  OPENCODE_ENABLE_EXA="${OPENCODE_ENABLE_EXA:-1}" \
	  OPENCODE_EXPERIMENTAL_LSP_TY="${OPENCODE_EXPERIMENTAL_LSP_TY:-1}" \
	  OPENCODE_EXPERIMENTAL_LSP_TOOL="${OPENCODE_EXPERIMENTAL_LSP_TOOL:-true}" \
	  bash -c "cd '$project_dir' && opencode serve --hostname '{{test_host}}' --port '{{test_port}}' --print-logs --log-level INFO" > "$sandbox/server.log" 2>&1 &
	server_pid=$!

	# Record metadata
	echo "$server_pid" > "$sandbox/.pid"
	echo "$sandbox" > "{{justfile_directory()}}/.test-sandbox-path"
	echo "$server_pid" > "{{justfile_directory()}}/.test-server.pid"

	# Health check: poll /global/health for up to 60s
	deadline=$((SECONDS + 60))
	while (( SECONDS < deadline )); do
	  if ! kill -0 "$server_pid" 2>/dev/null; then
	    echo "Server exited early (pid $server_pid). Logs:" >&2
	    tail -30 "$sandbox/server.log" >&2
	    rm -rf "$sandbox"
	    rm -f "{{justfile_directory()}}/.test-sandbox-path" "{{justfile_directory()}}/.test-server.pid" "{{test_sandbox_env}}"
	    exit 1
	  fi
	  if curl -sf "{{test_base_url}}/global/health" >/dev/null 2>&1; then
	    echo "Sandbox ready at {{test_base_url}} (pid $server_pid, path $sandbox)"
	    exit 0
	  fi
	  sleep 0.3
	done

	echo "Timed out waiting for server health check. Logs:" >&2
	tail -30 "$sandbox/server.log" >&2
	kill "$server_pid" 2>/dev/null || true
	rm -rf "$sandbox"
	rm -f "{{justfile_directory()}}/.test-sandbox-path" "{{justfile_directory()}}/.test-server.pid" "{{test_sandbox_env}}"
	exit 1

# Tear down the test sandbox: kill server, remove tmpdir.
[group('test')]
test-sandbox-down:
	#!/usr/bin/env bash
	set -euo pipefail
	sandbox_file="{{justfile_directory()}}/.test-sandbox-path"
	if [[ ! -f "$sandbox_file" ]]; then
	  echo "No sandbox running (missing .test-sandbox-path)" >&2
	  exit 0
	fi
	sandbox=$(cat "$sandbox_file")

	# Kill server
	if [[ -f "$sandbox/.pid" ]]; then
	  pid=$(cat "$sandbox/.pid")
	  if kill -0 "$pid" 2>/dev/null; then
	    kill "$pid"
	    for i in $(seq 1 50); do
	      kill -0 "$pid" 2>/dev/null || break
	      sleep 0.1
	    done
	    kill -9 "$pid" 2>/dev/null || true
	  fi
	fi

	rm -rf "$sandbox"
	rm -f "$sandbox_file" "{{justfile_directory()}}/.test-server.pid" "{{test_sandbox_env}}"
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
