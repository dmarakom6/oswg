"""Tests for the external tool runner (oswg test)."""

from pathlib import Path

import pytest

from oswg.core import test_runner as tr


def _inputs(**overrides):
    base = {
        "wordlist": Path("/tmp/w.txt"),
        "hashes": Path("/tmp/h.txt"),
        "mode": 0,
        "rules": None,
        "users": Path("/tmp/u.txt"),
        "host": "192.168.1.10",
        "service": "ssh",
        "url": "http://192.168.1.10",
        "capture": Path("/tmp/x.cap"),
    }
    base.update(overrides)
    return base


# --- args builders ---------------------------------------------------------


def test_hashcat_args(tmp_path):
    args = tr._hashcat_args(_inputs(), tmp_path)
    assert args[:7] == ["hashcat", "-m", "0", "-a", "0", "--potfile-path", str(tmp_path / "hashcat.potfile")]
    assert str(Path("/tmp/h.txt")) in args and str(Path("/tmp/w.txt")) in args
    assert tr._hashcat_args(_inputs(rules=Path("/tmp/r.txt")), tmp_path)[-2:] == ["-r", "/tmp/r.txt"]


def test_hashcat_args_requires_mode():
    with pytest.raises(tr.TestToolError, match="--mode"):
        tr._hashcat_args(_inputs(mode=None), Path("/tmp"))


def test_john_args():
    args = tr._john_args(_inputs(rules=Path("/tmp/r.txt")), Path("/tmp"))
    assert args == ["john", "--wordlist=/tmp/w.txt", "--rules=/tmp/r.txt", "/tmp/h.txt"]
    assert tr._john_post(_inputs(), Path("/tmp")) == ["john", "--show", "/tmp/h.txt"]


def test_network_tool_args():
    assert tr._hydra_args(_inputs(), Path("/tmp")) == [
        "hydra", "-L", "/tmp/u.txt", "-P", "/tmp/w.txt", "ssh://192.168.1.10"
    ]
    assert tr._medusa_args(_inputs(), Path("/tmp")) == [
        "medusa", "-h", "192.168.1.10", "-U", "/tmp/u.txt", "-P", "/tmp/w.txt", "-M", "ssh"
    ]
    assert tr._ncrack_args(_inputs(), Path("/tmp")) == [
        "ncrack", "-U", "/tmp/u.txt", "-P", "/tmp/w.txt", "ssh://192.168.1.10"
    ]


def test_network_tool_args_requires_host_service():
    for name in ("_hydra_args", "_medusa_args", "_ncrack_args"):
        with pytest.raises(tr.TestToolError, match="--host"):
            getattr(tr, name)(_inputs(host=None), Path("/tmp"))


def test_gobuster_args():
    assert tr._gobuster_args(_inputs(), Path("/tmp")) == [
        "gobuster", "dir", "-u", "http://192.168.1.10", "-w", "/tmp/w.txt"
    ]


def test_aircrack_args():
    assert tr._aircrack_args(_inputs(), Path("/tmp")) == ["aircrack-ng", "-w", "/tmp/w.txt", "/tmp/x.cap"]


# --- parsers ---------------------------------------------------------------


def test_parse_hashcat_potfile(tmp_path):
    (tmp_path / "hashcat.potfile").write_text(
        "5f4dcc3b5aa765d61d8327deb882cf99:password\n"
        "e10adc3949ba59abbe56e057f20f883e:123456\n"
    )
    result = tr._hashcat_parse("", tmp_path)
    assert result["found"] == 2
    assert result["entries"][0] == {"hash": "5f4dcc3b5aa765d61d8327deb882cf99", "password": "password"}


def test_parse_john_show():
    output = (
        "password1\n"
        "root:toor\n"
        "\n"
        "2 password hashes cracked, 0 left\n"
    )
    result = tr._john_parse(output, Path("/tmp"))
    assert result["found"] == 2
    assert result["entries"][0]["password"] == "password1"
    assert result["entries"][1]["password"] == "toor"


def test_parse_hydra():
    output = "[22][ssh] host:192.168.1.10   login:root   password:toor\n"
    result = tr._hydra_parse(output, Path("/tmp"))
    assert result["entries"][0] == {"user": "root", "password": "toor"}


def test_parse_medusa():
    output = "ACCOUNT FOUND: [ssh] Host: 192.168.1.10 User: root Password: toor [SUCCESS]\n"
    result = tr._medusa_parse(output, Path("/tmp"))
    assert result["entries"][0] == {"user": "root", "password": "toor"}


def test_parse_ncrack():
    output = "Discovered credentials for ssh on 192.168.1.10 22/tcp:  192.168.1.10:22: 'root' 'toor'\n"
    result = tr._ncrack_parse(output, Path("/tmp"))
    assert result["entries"][0] == {"user": "root", "password": "toor"}


def test_parse_gobuster():
    output = "/admin (Status: 301) [Size: 178]\n/index.html (Status: 200) [Size: 1567]\n"
    result = tr._gobuster_parse(output, Path("/tmp"))
    assert result["found"] == 2
    assert result["entries"][1] == {"path": "/index.html", "status": "200"}


def test_parse_aircrack():
    output = "                     KEY FOUND! [ hello_world ]\n"
    result = tr._aircrack_parse(output, Path("/tmp"))
    assert result["entries"] == [{"key": "hello_world"}]


# --- run -------------------------------------------------------------------


class _FakeProc:
    def __init__(self, output: str):
        self.stdout = iter(output.splitlines(keepends=True))

    def wait(self):
        pass


def test_run_mocked(monkeypatch, tmp_path):
    output = "[22][ssh] host:192.168.1.10   login:root   password:toor\n"
    monkeypatch.setattr(tr.subprocess, "Popen", lambda *a, **k: _FakeProc(output))
    monkeypatch.setattr(tr.shutil, "which", lambda name: "/usr/bin/hydra")

    result = tr.run("hydra", _inputs())
    assert result["tool"] == "hydra"
    assert result["found"] == 1
    assert result["entries"][0]["password"] == "toor"


def test_run_unknown_tool():
    with pytest.raises(tr.TestToolError, match="Unknown tool"):
        tr.run("nmap", _inputs())


def test_run_missing_tool(monkeypatch):
    monkeypatch.setattr(tr.shutil, "which", lambda name: None)
    with pytest.raises(tr.TestToolError, match="oswg setup"):
        tr.run("hashcat", _inputs())
