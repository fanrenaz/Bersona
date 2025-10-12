import re
from pathlib import Path

import bersona

def test_version_matches_pyproject():
    pkg_version = bersona.__version__
    pyproject = Path(__file__).resolve().parents[1] / 'pyproject.toml'
    text = pyproject.read_text(encoding='utf-8')
    m = re.search(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text, re.MULTILINE)
    assert m, 'Version not found in pyproject.toml'
    assert m.group(1) == pkg_version, f"Mismatch: pyproject={m.group(1)} package={pkg_version}"