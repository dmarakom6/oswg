"""Tests for the optional-extras detection (oswg setup)."""

from pathlib import Path

from oswg import setup as setup_mod


def test_browser_cache_dir_darwin(monkeypatch, tmp_path):
    monkeypatch.setattr(setup_mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert setup_mod.browser_cache_dir() == tmp_path / "Library" / "Caches" / "ms-playwright"


def test_browser_cache_dir_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(setup_mod.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert setup_mod.browser_cache_dir() == tmp_path / ".cache" / "ms-playwright"


def test_chromium_installed(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    (cache / "chromium-1234").mkdir(parents=True)
    monkeypatch.setattr(setup_mod, "browser_cache_dir", lambda: cache)
    assert setup_mod.chromium_installed() is True

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(setup_mod, "browser_cache_dir", lambda: empty)
    assert setup_mod.chromium_installed() is False


def test_has_module():
    assert setup_mod.has_module("oswg") is True
    assert setup_mod.has_module("definitely_not_a_module_xyz") is False


def test_tool(monkeypatch, tmp_path):
    fake = tmp_path / "hashcat"
    fake.write_text("x")
    fake.chmod(0o755)
    monkeypatch.setattr(
        setup_mod.shutil,
        "which",
        lambda name: str(fake) if name == "hashcat" else None,
    )
    assert setup_mod.tool("hashcat") == str(fake)
    assert setup_mod.tool("john") is None


def test_hashcat_hint(monkeypatch):
    monkeypatch.setattr(setup_mod.platform, "system", lambda: "Darwin")
    assert "brew" in setup_mod.hashcat_hint()
    monkeypatch.setattr(setup_mod.platform, "system", lambda: "Windows")
    assert "choco" in setup_mod.hashcat_hint()


def test_pip_target(monkeypatch):
    monkeypatch.setattr(setup_mod, "editable_source_dir", lambda: None)
    assert setup_mod.pip_target("js") == "oswg[js]"
    monkeypatch.setattr(setup_mod, "editable_source_dir", lambda: Path("/src/oswg"))
    assert setup_mod.pip_target("auth") == "/src/oswg[auth]"


def test_detect_shape(monkeypatch):
    monkeypatch.setattr(setup_mod, "has_module", lambda name: name == "playwright")
    monkeypatch.setattr(setup_mod, "chromium_installed", lambda: True)
    monkeypatch.setattr(setup_mod, "tool", lambda name: None)
    monkeypatch.setattr(setup_mod, "in_venv", lambda: True)
    monkeypatch.setattr(setup_mod, "is_frozen", lambda: False)

    d = setup_mod.detect()
    assert d["js"] is True
    assert d["auth"] is False
    assert d["chromium"] is True
    assert d["venv"] is True
    assert d["frozen"] is False
    assert set(d["test_tools"]) == {"hashcat", "john", "hydra", "medusa", "ncrack", "gobuster", "aircrack-ng"}
