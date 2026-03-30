# codex-cli-from-vscode

This project provides a small Python launcher named `codex-launcher.py` that forwards execution to the Codex CLI binary bundled inside the VS Code OpenAI extension currently registered in `extensions.json`.

## Resolution flow

1. Resolve the real path of `codex-launcher.py` so symlinked execution still finds the project files.
2. Load `config.json`.
3. Read `extensions_dir` from config.
4. Parse `extensions.json` inside that directory.
5. Find the `openai.chatgpt` entry that VS Code has registered.
6. Use `location.path` when present, or fall back to `relativeLocation`.
7. Resolve the platform-specific bundled `codex` binary inside that exact extension directory.
8. `exec` the real binary and forward all CLI arguments unchanged.

## Configuration

`config.json` is gitignored. The expected shape is:

```json
{
  "extensions_dir": "/home/jamesn/vscode/server-data/extensions"
}
```

`config.example.json` is tracked as a template, and this repo also includes a local `config.json` for the requested base directory.

## Symlink setup

```bash
chmod +x /home/jamesn/repo/ai-general/codex-cli-from-vscode/codex-launcher.py
ln -sf /home/jamesn/repo/ai-general/codex-cli-from-vscode/codex-launcher.py ~/.local/bin/codex
```

Make sure `~/.local/bin` is on your `PATH`.
