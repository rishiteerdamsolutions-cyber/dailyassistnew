from pathlib import Path
from unittest.mock import patch

from aha.tesseract_runtime import ensure_tesseract_configured, resolve_tesseract_cmd


def test_resolve_uses_bundled_tesseract_when_present(tmp_path, monkeypatch):
    bundle = tmp_path / "tesseract"
    (bundle / "bin").mkdir(parents=True)
    binary = bundle / "bin" / "tesseract"
    binary.write_text("", encoding="utf-8")
    (bundle / "tessdata").mkdir()
    (bundle / "tessdata" / "eng.traineddata").write_text("", encoding="utf-8")

    with patch("aha.tesseract_runtime._tesseract_search_roots", return_value=[bundle]):
        cmd = resolve_tesseract_cmd()
    assert cmd == str(binary)


def test_ensure_configures_pytesseract(tmp_path, monkeypatch):
    bundle = tmp_path / "tesseract"
    (bundle / "bin").mkdir(parents=True)
    binary = bundle / "bin" / "tesseract"
    binary.write_text("", encoding="utf-8")

    with patch("aha.tesseract_runtime._tesseract_search_roots", return_value=[bundle]):
        cmd = ensure_tesseract_configured()
    assert cmd == str(binary)
    import pytesseract

    assert pytesseract.pytesseract.tesseract_cmd == str(binary)
