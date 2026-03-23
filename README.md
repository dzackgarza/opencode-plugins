[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)

# OpenCode Plugins

Collection of standalone OpenCode plugin packages and shared support code.

## Plugins

- **[opencode-plugin-improved-task](./plugins/opencode-plugin-improved-task/README.md)**: Plugin-backed task management.
- **[opencode-plugin-improved-todowrite](./plugins/opencode-plugin-improved-todowrite/README.md)**: Hierarchical todo tree tools with MCP wrapper.
- **[opencode-plugin-improved-webtools](./plugins/opencode-plugin-improved-webtools/README.md)**: Web fetching and searching tools with MCP wrapper.
- **[opencode-plugin-prompt-transformer](./plugins/opencode-plugin-prompt-transformer/README.md)**: Prompt-tier routing hook.
- **[opencode-memory-plugin](./plugins/opencode-memory-plugin/README.md)**: File-backed memory tools plus MCP wrapper.
- **[opencode-plugin-reminder-injection](./plugins/opencode-plugin-reminder-injection/README.md)**: Skill-reminder message transform hook.
- **[opencode-zotero-plugin](./plugins/opencode-zotero-plugin/README.md)**: Zotero toolkit and OpenCode adapter surfaces.

## Testing

CI owns proof execution. Repos should call the centralized reusable workflows in this repo instead of inventing repo-local CI logic:

- [`python-cli-ci.yml`](/home/dzack/opencode-plugins/.github/workflows/python-cli-ci.yml)
- [`python-cli-publish.yml`](/home/dzack/opencode-plugins/.github/workflows/python-cli-publish.yml)
- [`bun-plugin-ci.yml`](/home/dzack/opencode-plugins/.github/workflows/bun-plugin-ci.yml)
- [`bun-plugin-publish.yml`](/home/dzack/opencode-plugins/.github/workflows/bun-plugin-publish.yml)

When a proof workflow needs OpenCode, rely on standard config precedence:

- global config at `~/.config/opencode/opencode.json` when needed
- project config at repo-root `opencode.json`
- no `OPENCODE_CONFIG` / `OPENCODE_CONFIG_DIR` path overrides unless there is a documented reason they are required

The older sandbox recipes are deprecated and are no longer the CI source of truth. Refer to individual package READMEs and [`CONTINUATION.md`](/home/dzack/opencode-plugins/CONTINUATION.md) for the active migration state.
