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
# test-sandbox-up creates an isolated opencode instance that cannot see host
# configs, starts `opencode serve` on the canonical address, health-checks it,
# and writes PID/path metadata to .test-server.pid and .test-sandbox-path.
# test-sandbox-down tears it all down.
#
# Usage:
#   just test-sandbox-up
#   OPENCODE_BASE_URL=http://127.0.0.1:4097 bun test   # (tests set OPENCODE_CONFIG per-plugin)
#   just test-sandbox-down

test_port := "4097"
test_host := "127.0.0.1"
test_base_url := "http://" + test_host + ":" + test_port

# Stand up an isolated opencode sandbox and serve on 127.0.0.1:4097.
# Copies the global opencode config into the sandbox. Health-checks before returning.
[group('test')]
test-sandbox-up:
	#!/usr/bin/env bash
	set -euo pipefail

	# Refuse if already running
	if [[ -f "{{justfile_directory()}}/.test-sandbox-path" ]]; then
	  sandbox=$(cat "{{justfile_directory()}}/.test-sandbox-path")
	  if [[ -f "$sandbox/.pid" ]] && kill -0 "$(cat "$sandbox/.pid")" 2>/dev/null; then
	    echo "Sandbox already running (pid $(cat "$sandbox/.pid"), path $sandbox)" >&2
	    exit 1
	  fi
	  # Stale metadata — clean up
	  rm -rf "$sandbox"
	  rm -f "{{justfile_directory()}}/.test-sandbox-path" "{{justfile_directory()}}/.test-server.pid"
	fi

	# Create isolated tmpdir
	sandbox=$(mktemp -d "/tmp/opencode-test-XXXXXXXXXX")
	config_home="$sandbox/config"
	cache_home="$sandbox/cache"
	state_home="$sandbox/state"
	data_home="$sandbox/data"
	fake_home="$sandbox/home"
	mkdir -p "$config_home/opencode" "$cache_home" "$state_home" "$data_home" "$fake_home"

	# Copy global opencode config into sandbox
	global_config="$HOME/.config/opencode/opencode.json"
	if [[ -f "$global_config" ]]; then
	  cp "$global_config" "$config_home/opencode/opencode.json"
	fi

	# Start server with fully isolated env
	HOME="$fake_home" \
	XDG_CONFIG_HOME="$config_home" \
	XDG_CACHE_HOME="$cache_home" \
	XDG_STATE_HOME="$state_home" \
	XDG_DATA_HOME="$data_home" \
	OPENCODE_BASE_URL="{{test_base_url}}" \
	opencode serve \
	  --hostname "{{test_host}}" \
	  --port "{{test_port}}" \
	  --print-logs \
	  --log-level INFO \
	  > "$sandbox/server.log" 2>&1 &
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
	    rm -f "{{justfile_directory()}}/.test-sandbox-path" "{{justfile_directory()}}/.test-server.pid"
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
	rm -f "{{justfile_directory()}}/.test-sandbox-path" "{{justfile_directory()}}/.test-server.pid"
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
	rm -f "$sandbox_file" "{{justfile_directory()}}/.test-server.pid"
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
