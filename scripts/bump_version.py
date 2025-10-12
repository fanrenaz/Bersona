#!/usr/bin/env python3
"""Simple semantic version bump script for pyproject.toml.

Usage:
  python scripts/bump_version.py patch
  python scripts/bump_version.py minor
  python scripts/bump_version.py major

Updates:
  - pyproject.toml version field
  - src/bersona/_version.py __version__ constant

Does not create git tags automatically (recommend using separate release step / CI).
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / 'pyproject.toml'
VERSION_FILE = ROOT / 'src' / 'bersona' / '_version.py'

SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')


def read_current_version() -> str:
    text = PYPROJECT.read_text(encoding='utf-8')
    m = re.search(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text, re.MULTILINE)
    if not m:
        raise SystemExit('Version not found in pyproject.toml')
    return m.group(1)


def bump(ver: str, kind: str) -> str:
    m = SEMVER_RE.match(ver)
    if not m:
        raise SystemExit(f'Invalid semver: {ver}')
    major, minor, patch = map(int, m.groups())
    if kind == 'patch':
        patch += 1
    elif kind == 'minor':
        minor += 1
        patch = 0
    elif kind == 'major':
        major += 1
        minor = 0
        patch = 0
    else:
        raise SystemExit('Kind must be one of major/minor/patch')
    return f'{major}.{minor}.{patch}'


def write_pyproject(new_version: str) -> None:
    text = PYPROJECT.read_text(encoding='utf-8')
    new_text = re.sub(r'(^version\s*=\s*")([0-9]+\.[0-9]+\.[0-9]+)(")',
                      rf'\g<1>{new_version}\3', text, flags=re.MULTILINE)
    PYPROJECT.write_text(new_text, encoding='utf-8')


def write_version_file(new_version: str) -> None:
    vf_text = VERSION_FILE.read_text(encoding='utf-8')
    new_vf = re.sub(r'(__version__\s*=\s*")([0-9]+\.[0-9]+\.[0-9]+)(")',
                    rf'\g<1>{new_version}\3', vf_text)
    VERSION_FILE.write_text(new_vf, encoding='utf-8')


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('Usage: bump_version.py [major|minor|patch]')
        return 1
    kind = argv[1]
    current = read_current_version()
    new_version = bump(current, kind)
    write_pyproject(new_version)
    write_version_file(new_version)
    print(f'Version bumped: {current} -> {new_version}')
    print('Remember to commit changes and create a git tag if releasing.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
