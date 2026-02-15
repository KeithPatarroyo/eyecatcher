"""Tests for codegen sync check (make check-generate)."""

import subprocess
import sys

from eyecatcher import get_root_dir


def test_check_codegen_sync_exits_zero_when_up_to_date():
    """check_codegen_sync.py exits 0 when generated files are not stale.

    If this fails, run `make generate` and commit updated generated files.
    """
    root = get_root_dir()
    result = subprocess.run(
        [sys.executable, "scripts/check_codegen_sync.py"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        result.stderr.strip()
        or result.stdout.strip()
        or "Generated files are stale. Run: make generate."
    )
