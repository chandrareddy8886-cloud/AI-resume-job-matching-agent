from pathlib import Path


def test_workspace_script_has_no_literal_escape_before_try():
    html = (Path(__file__).parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert r"\\ntry{" not in html


def test_resume_picker_has_selection_and_drop_handlers():
    html = (Path(__file__).parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "fileInput.click()" in html
    assert "fileInput.addEventListener('change'" in html
    assert "drop.addEventListener('drop'" in html
    assert "fileInput.files=e.dataTransfer.files" in html
