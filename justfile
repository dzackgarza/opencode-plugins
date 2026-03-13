# Root justfile for Opencode Plugins

plugins := "improved-task improved-todowrite improved-webtools mcp-shim opencode-manager opencode-postgres-memory-plugin opencode-time-travel-plugin opencode-zotero-plugin prompt-router skill-reminder-injection"

# Setup npm trusted publisher for ALL plugins (one-time manual setup)
# This will pause and prompt for 2FA for each plugin.
setup-all-npm-trust:
    #!/usr/bin/env bash
    set -euo pipefail
    for plugin in {{plugins}}; do
        echo "--- Setting up OIDC trust for $plugin ---"
        just --justfile "$plugin/justfile" --working-directory "$plugin" setup-npm-trust
    done

# Initial publish for ALL plugins (one-time manual setup)
# This will pause and prompt for 2FA for each plugin.
publish-all:
    #!/usr/bin/env bash
    set -euo pipefail
    for plugin in {{plugins}}; do
        echo "--- Publishing $plugin ---"
        just --justfile "$plugin/justfile" --working-directory "$plugin" publish
    done
