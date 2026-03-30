#!/usr/bin/env python3

import json
import os
import platform
import sys
from pathlib import Path


class LauncherError(Exception):
    pass


def load_json_file(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LauncherError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LauncherError(f"Invalid JSON in {path}: {exc}") from exc


def load_config(project_dir: Path) -> Path:
    config_path = project_dir / "config.json"
    data = load_json_file(config_path)
    if not isinstance(data, dict):
        raise LauncherError(f"Expected {config_path} to contain a JSON object")

    extensions_dir = data.get("extensions_dir")
    if not isinstance(extensions_dir, str) or not extensions_dir:
        raise LauncherError("config.json must define a non-empty string field: extensions_dir")

    resolved = Path(extensions_dir)
    if not resolved.is_absolute():
        raise LauncherError("extensions_dir must be an absolute path")
    if not resolved.is_dir():
        raise LauncherError(f"Configured extensions_dir does not exist: {resolved}")
    return resolved


def load_extensions_index(extensions_dir: Path) -> list[object]:
    index_path = extensions_dir / "extensions.json"
    data = load_json_file(index_path)
    if not isinstance(data, list):
        raise LauncherError(f"Expected {index_path} to contain a JSON array")
    return data


def resolve_registered_extension_dir(extensions_dir: Path) -> Path:
    entries = load_extensions_index(extensions_dir)
    matches = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("identifier")
        if not isinstance(identifier, dict):
            continue
        if identifier.get("id") != "openai.chatgpt":
            continue
        matches.append(entry)

    if not matches:
        raise LauncherError(
            f"No openai.chatgpt entry found in {extensions_dir / 'extensions.json'}"
        )
    if len(matches) > 1:
        raise LauncherError(
            "Multiple openai.chatgpt entries found in extensions.json; "
            "unable to determine the active extension directory safely"
        )

    entry = matches[0]
    location = entry.get("location")
    if isinstance(location, dict) and location.get("scheme") == "file":
        location_path = location.get("path")
        if isinstance(location_path, str) and location_path:
            resolved = Path(location_path)
            if resolved.is_dir():
                return resolved
            raise LauncherError(
                f"Registered openai.chatgpt location does not exist: {resolved}"
            )

    relative_location = entry.get("relativeLocation")
    if isinstance(relative_location, str) and relative_location:
        resolved = extensions_dir / relative_location
        if resolved.is_dir():
            return resolved
        raise LauncherError(
            f"Registered openai.chatgpt relativeLocation does not exist: {resolved}"
        )

    raise LauncherError(
        "The openai.chatgpt entry in extensions.json did not contain a usable location"
    )


def resolve_binary_relative_path() -> Path:
    system = platform.system().lower()
    machine = platform.machine().lower()

    binary_map = {
        ("linux", "x86_64"): Path("bin/linux-x86_64/codex"),
        ("linux", "amd64"): Path("bin/linux-x86_64/codex"),
        ("linux", "aarch64"): Path("bin/linux-arm64/codex"),
        ("linux", "arm64"): Path("bin/linux-arm64/codex"),
        ("darwin", "x86_64"): Path("bin/darwin-x86_64/codex"),
        ("darwin", "arm64"): Path("bin/darwin-arm64/codex"),
    }

    try:
        return binary_map[(system, machine)]
    except KeyError as exc:
        raise LauncherError(
            f"Unsupported platform for Codex binary lookup: {system}/{machine}"
        ) from exc


def resolve_fallback_binary_relative_path(extension_dir: Path) -> Path:
    bin_dir = extension_dir / "bin"
    if not bin_dir.is_dir():
        raise LauncherError(f"Codex bin directory not found: {bin_dir}")

    candidates = sorted(
        child for child in bin_dir.iterdir() if child.is_dir() and not child.name.startswith(".")
    )
    if not candidates:
        raise LauncherError(f"No non-hidden platform directories found in: {bin_dir}")

    return Path("bin") / candidates[0].name / "codex"


def resolve_binary_path(extension_dir: Path) -> Path:
    try:
        binary_relative_path = resolve_binary_relative_path()
    except LauncherError:
        binary_relative_path = resolve_fallback_binary_relative_path(extension_dir)

    binary_path = extension_dir / binary_relative_path
    if not binary_path.is_file():
        raise LauncherError(f"Codex binary not found at expected path: {binary_path}")
    if not os.access(binary_path, os.X_OK):
        raise LauncherError(f"Codex binary is not executable: {binary_path}")
    return binary_path


def main() -> int:
    project_dir = Path(__file__).resolve().parent
    extensions_dir = load_config(project_dir)
    extension_dir = resolve_registered_extension_dir(extensions_dir)
    binary_path = resolve_binary_path(extension_dir)
    os.execv(str(binary_path), [str(binary_path), *sys.argv[1:]])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LauncherError as exc:
        print(f"codex launcher error: {exc}", file=sys.stderr)
        raise SystemExit(1)
