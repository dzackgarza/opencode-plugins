set fallback := true
# Root justfile for Opencode Plugins

plugins := "plugins/opencode-memory-plugin plugins/opencode-plugin-improved-task plugins/opencode-plugin-improved-todowrite plugins/opencode-plugin-improved-webtools plugins/opencode-plugin-prompt-transformer plugins/opencode-plugin-reminder-injection plugins/opencode-zotero-plugin"

default:
	@just --list

[private]
_run-plugin-recipe recipe:
	#!/usr/bin/env bash
	set -euo pipefail
	for plugin in {{plugins}}; do
		if [[ -f "$plugin/justfile" ]]; then
			echo "Running {{recipe}} for $plugin"
			just --justfile "$plugin/justfile" --working-directory "$plugin" "{{recipe}}"
		fi
	done

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
	just --justfile "{{justfile()}}" _run-plugin-recipe setup-npm-trust

# Initial publish for ALL plugins
publish-all:
	just --justfile "{{justfile()}}" _run-plugin-recipe publish

# Run the public verification gate for all package repos.
test-all:
	just --justfile "{{justfile()}}" _run-plugin-recipe test

# Dashboard recipes
[private]
_check-dashboard:
	@bunx tsc dashboard.ts --noEmit --esModuleInterop --skipLibCheck --target esnext --lib esnext,dom

build-dashboard: _check-dashboard
	@bunx tsc dashboard.ts --outFile /home/dzack/www/html/dashboard.js --esModuleInterop --skipLibCheck --target esnext --lib esnext,dom

refresh-dashboard-token:
	@python3 -c "import subprocess; token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip(); open('/home/dzack/www/html/config.js', 'w').write(f'window.GITHUB_TOKEN = \"{token}\";\n')"

update-usage:
        #!/usr/bin/env bash
        set -euo pipefail
        source ~/.envrc 2>/dev/null || true
        uvx --from git+https://github.com/dzackgarza/usage-limits usage-limits --json > /home/dzack/www/html/usage.json

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
