from pathlib import Path
import shutil
import subprocess


def test_workspace_script_has_no_literal_escape_before_try():
    html = (Path(__file__).parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "\\ntry{" not in html


def test_resume_picker_has_selection_and_drop_handlers():
    html = (Path(__file__).parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "fileInput.click()" in html
    assert "fileInput.addEventListener('change'" in html
    assert "drop.addEventListener('drop'" in html
    assert "fileInput.files=e.dataTransfer.files" in html


def test_workspace_javascript_parses_when_node_is_available(tmp_path):
    node = shutil.which("node")
    if not node:
        return
    html = (Path(__file__).parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    script_file = tmp_path / "workspace.js"
    script_file.write_text(script, encoding="utf-8")
    subprocess.run([node, "--check", str(script_file)], check=True, capture_output=True, text=True)
