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

Integration tests run against an isolated opencode server that cannot see host configs. The top-level justfile manages the sandbox lifecycle:

```bash
just test-sandbox-up     # creates tmpdir, starts opencode serve on 127.0.0.1:4097, health-checks
just test-sandbox-down   # kills server, removes tmpdir
```

`test-sandbox-up` creates a tmpdir with isolated `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, and `XDG_DATA_HOME`. It copies the global opencode config (`~/.config/opencode/opencode.json`) into the sandbox so the server has provider credentials and baseline settings, then starts `opencode serve` and waits for `/global/health` to return before completing.

The canonical test address is always `http://127.0.0.1:4097`.

**Per-plugin config:** Tests set `OPENCODE_CONFIG` to point at their plugin's `.config/opencode.json`, which extends the global config with plugin-specific agents, permissions, and plugin references. This follows opencode's config precedence (global → custom path → project).

Refer to individual package READMEs for plugin-specific test details. For a compliance rubric, see the `opencode-plugin-development` skill.
