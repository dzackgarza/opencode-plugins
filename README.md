[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)

# OpenCode Plugins

Collection of standalone OpenCode plugin packages and shared support code.

## Plugins

- **[opencode-plugin-improved-task](./opencode-plugin-improved-task/README.md)**: Plugin-backed task management.
- **[opencode-plugin-improved-todowrite](./opencode-plugin-improved-todowrite/README.md)**: Hierarchical todo tree tools with MCP wrapper.
- **[opencode-plugin-improved-webtools](./opencode-plugin-improved-webtools/README.md)**: Web fetching and searching tools with MCP wrapper.
- **[opencode-plugin-prompt-transformer](./opencode-plugin-prompt-transformer/README.md)**: Prompt-tier routing hook.
- **[opencode-plugin-mcp-shim](./opencode-plugin-mcp-shim/README.md)**: Shared TypeScript executor for MCP wrappers.
- **[opencode-zotero-plugin](./opencode-zotero-plugin/README.md)**: Zotero toolkit and OpenCode adapter surfaces.

## Testing

CI owns proof execution. Python CLI repos should call the centralized reusable workflows at [`python-cli-ci.yml`](/home/dzack/opencode-plugins/.github/workflows/python-cli-ci.yml) and [`python-cli-publish.yml`](/home/dzack/opencode-plugins/.github/workflows/python-cli-publish.yml) instead of inventing repo-local CI logic.

When a proof workflow needs OpenCode, rely on standard config precedence:

- global config at `~/.config/opencode/opencode.json` when needed
- project config at repo-root `opencode.json`
- no `OPENCODE_CONFIG` / `OPENCODE_CONFIG_DIR` path overrides unless there is a documented reason they are required

The older sandbox recipes are no longer the CI source of truth. Refer to individual package READMEs and [`CONTINUATION.md`](/home/dzack/opencode-plugins/CONTINUATION.md) for the active migration state.
