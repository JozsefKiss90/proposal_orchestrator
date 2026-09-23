"""Tests for runner.atomic_write — the shared atomic-write helpers.

Covers the tricky parts the callers rely on: atomic overwrite, and
cleanup-on-failure (a failed write leaves neither a partial target nor a stray
temp file).  Byte-level correctness of the JSON serialisation is additionally
guaranteed by the byte-equal replay tests of the callers (section assembler,
unit-cost budget).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.atomic_write import atomic_write_json, atomic_write_text, atomic_write_via


class TestAtomicWriteJson:
    def test_writes_pretty_json_creating_parents(self, tmp_path: Path) -> None:
        out = tmp_path / "a" / "b" / "x.json"
        atomic_write_json({"k": "v", "n": 1}, out)
        assert out.is_file()
        assert json.loads(out.read_text("utf-8")) == {"k": "v", "n": 1}
        # Pretty-printed with indent=2 (the canonical serialisation).
        assert out.read_text("utf-8") == json.dumps(
            {"k": "v", "n": 1}, indent=2, ensure_ascii=False
        )

    def test_overwrites_existing_without_temp_leftover(self, tmp_path: Path) -> None:
        out = tmp_path / "x.json"
        atomic_write_json({"v": 1}, out, prefix="t_")
        atomic_write_json({"v": 2}, out, prefix="t_")
        assert json.loads(out.read_text("utf-8")) == {"v": 2}
        assert list(tmp_path.glob("*.tmp")) == []

    def test_non_serialisable_leaves_no_partial(self, tmp_path: Path) -> None:
        out = tmp_path / "x.json"
        with pytest.raises(TypeError):
            atomic_write_json({"bad": object()}, out)
        assert not out.exists()
        assert list(tmp_path.glob("*.tmp")) == []


class TestAtomicWriteText:
    def test_writes_utf8_text_creating_parents(self, tmp_path: Path) -> None:
        out = tmp_path / "a" / "b" / "note.md"
        atomic_write_text("# Title\n\nbody with ünïcode\n", out)
        assert out.read_text("utf-8") == "# Title\n\nbody with ünïcode\n"

    def test_newlines_written_verbatim(self, tmp_path: Path) -> None:
        # \n is not translated (byte-identical across platforms).
        out = tmp_path / "x.md"
        atomic_write_text("a\nb\nc", out)
        assert out.read_bytes() == b"a\nb\nc"

    def test_overwrites_without_temp_leftover(self, tmp_path: Path) -> None:
        out = tmp_path / "x.md"
        atomic_write_text("one", out, prefix="t_")
        atomic_write_text("two", out, prefix="t_")
        assert out.read_text("utf-8") == "two"
        assert list(tmp_path.glob("*.tmp")) == []


class TestAtomicWriteVia:
    def test_save_callback_produces_file(self, tmp_path: Path) -> None:
        out = tmp_path / "sub" / "doc.bin"

        def _save(path: str) -> None:
            Path(path).write_bytes(b"BINARY")

        atomic_write_via(out, _save, prefix="d_")
        assert out.read_bytes() == b"BINARY"
        assert list((tmp_path / "sub").glob("*.tmp")) == []

    def test_failing_save_cleans_up_and_preserves_target(self, tmp_path: Path) -> None:
        out = tmp_path / "doc.bin"
        out.write_bytes(b"ORIGINAL")

        def _boom(path: str) -> None:
            raise RuntimeError("save failed")

        with pytest.raises(RuntimeError, match="save failed"):
            atomic_write_via(out, _boom)
        # The pre-existing target is untouched and no temp file remains.
        assert out.read_bytes() == b"ORIGINAL"
        assert list(tmp_path.glob("*.tmp")) == []
