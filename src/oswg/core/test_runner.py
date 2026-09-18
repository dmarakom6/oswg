"""Drive external cracking tools (hashcat, john, hydra, ...) with a wordlist."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TOOLS = ("hashcat", "john", "hydra", "medusa", "ncrack", "gobuster", "aircrack-ng")


class TestToolError(RuntimeError):
    """Raised when a tool is missing or its inputs are incomplete."""


def available() -> dict[str, bool]:
    return {name: shutil.which(name) is not None for name in TOOLS}


def _req(inputs: dict, key: str) -> Path:
    value = inputs.get(key)
    if not value:
        raise TestToolError(f"--{key} is required for this tool")
    return Path(value)


# --- hashcat ---------------------------------------------------------------


def _hashcat_args(inputs: dict, tmpdir: Path) -> list[str]:
    hashes = _req(inputs, "hashes")
    wordlist = _req(inputs, "wordlist")
    mode = inputs.get("mode")
    if mode is None:
        raise TestToolError("--mode is required for hashcat (e.g. 0=MD5, 1000=NTLM)")
    args = [
        "hashcat",
        "-m", str(mode),
        "-a", "0",
        "--potfile-path", str(tmpdir / "hashcat.potfile"),
        str(hashes),
        str(wordlist),
    ]
    if inputs.get("rules"):
        args += ["-r", str(inputs["rules"])]
    return args


def _hashcat_parse(text: str, tmpdir: Path) -> dict:
    potfile = tmpdir / "hashcat.potfile"
    entries = []
    if potfile.exists():
        for line in potfile.read_text(errors="ignore").splitlines():
            if ":" in line:
                hash_, password = line.split(":", 1)
                entries.append({"hash": hash_, "password": password})
    return {"found": len(entries), "entries": entries, "kind": "hash"}


# --- john ------------------------------------------------------------------


def _john_args(inputs: dict, tmpdir: Path) -> list[str]:
    hashes = _req(inputs, "hashes")
    wordlist = _req(inputs, "wordlist")
    args = ["john", f"--wordlist={wordlist}"]
    if inputs.get("rules"):
        args.append(f"--rules={inputs['rules']}")
    args.append(str(hashes))
    return args


def _john_post(inputs: dict, tmpdir: Path) -> list[str]:
    return ["john", "--show", str(_req(inputs, "hashes"))]


def _john_parse(text: str, tmpdir: Path) -> dict:
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if " hashes cracked" in line or "No password hashes left" in line:
            continue
        if ":" in line:
            parts = line.split(":")
            password = parts[1] if len(parts) > 1 and parts[1] else parts[0]
        else:
            password = line
        entries.append({"password": password})
    return {"found": len(entries), "entries": entries, "kind": "hash"}


# --- hydra -----------------------------------------------------------------

_HYDRA_RE = re.compile(r"login:\s*(\S+)\s+password:\s*(\S+)")


def _hydra_args(inputs: dict, tmpdir: Path) -> list[str]:
    users = _req(inputs, "users")
    wordlist = _req(inputs, "wordlist")
    host = inputs.get("host")
    service = inputs.get("service")
    if not host or not service:
        raise TestToolError("--host and --service are required for hydra")
    return ["hydra", "-L", str(users), "-P", str(wordlist), f"{service}://{host}"]


def _hydra_parse(text: str, tmpdir: Path) -> dict:
    entries = [{"user": u, "password": p} for u, p in _HYDRA_RE.findall(text)]
    return {"found": len(entries), "entries": entries, "kind": "login"}


# --- medusa ----------------------------------------------------------------

_MEDUSA_RE = re.compile(r"User:\s*(\S+)\s+Password:\s*(\S+)")


def _medusa_args(inputs: dict, tmpdir: Path) -> list[str]:
    users = _req(inputs, "users")
    wordlist = _req(inputs, "wordlist")
    host = inputs.get("host")
    service = inputs.get("service")
    if not host or not service:
        raise TestToolError("--host and --service are required for medusa")
    return ["medusa", "-h", str(host), "-U", str(users), "-P", str(wordlist), "-M", str(service)]


def _medusa_parse(text: str, tmpdir: Path) -> dict:
    entries = [{"user": u, "password": p} for u, p in _MEDUSA_RE.findall(text)]
    return {"found": len(entries), "entries": entries, "kind": "login"}


# --- ncrack ----------------------------------------------------------------

_NCRACK_RE = re.compile(r"'([^']+)'\s+'([^']+)'")


def _ncrack_args(inputs: dict, tmpdir: Path) -> list[str]:
    users = _req(inputs, "users")
    wordlist = _req(inputs, "wordlist")
    host = inputs.get("host")
    service = inputs.get("service")
    if not host or not service:
        raise TestToolError("--host and --service are required for ncrack")
    return ["ncrack", "-U", str(users), "-P", str(wordlist), f"{service}://{host}"]


def _ncrack_parse(text: str, tmpdir: Path) -> dict:
    entries = [{"user": u, "password": p} for u, p in _NCRACK_RE.findall(text)]
    return {"found": len(entries), "entries": entries, "kind": "login"}


# --- gobuster --------------------------------------------------------------

_GOBUSTER_RE = re.compile(r"^(\S+)\s+\(Status:\s+(\d+)\)", re.M)


def _gobuster_args(inputs: dict, tmpdir: Path) -> list[str]:
    url = inputs.get("url")
    if not url:
        raise TestToolError("--url is required for gobuster")
    return ["gobuster", "dir", "-u", url, "-w", str(_req(inputs, "wordlist"))]


def _gobuster_parse(text: str, tmpdir: Path) -> dict:
    entries = [{"path": path, "status": status} for path, status in _GOBUSTER_RE.findall(text)]
    return {"found": len(entries), "entries": entries, "kind": "path"}


# --- aircrack-ng -----------------------------------------------------------

_AIRCRACK_RE = re.compile(r"KEY FOUND!\s*\[\s*([^\]]+?)\s*\]")


def _aircrack_args(inputs: dict, tmpdir: Path) -> list[str]:
    capture = _req(inputs, "capture")
    return ["aircrack-ng", "-w", str(_req(inputs, "wordlist")), str(capture)]


def _aircrack_parse(text: str, tmpdir: Path) -> dict:
    match = _AIRCRACK_RE.search(text)
    entries = [{"key": match.group(1).strip()}] if match else []
    return {"found": len(entries), "entries": entries, "kind": "key"}


# --- dispatch --------------------------------------------------------------

_PROFILES = {
    "hashcat": {"args": _hashcat_args, "parse": _hashcat_parse},
    "john": {"args": _john_args, "parse": _john_parse, "post": _john_post},
    "hydra": {"args": _hydra_args, "parse": _hydra_parse},
    "medusa": {"args": _medusa_args, "parse": _medusa_parse},
    "ncrack": {"args": _ncrack_args, "parse": _ncrack_parse},
    "gobuster": {"args": _gobuster_args, "parse": _gobuster_parse},
    "aircrack-ng": {"args": _aircrack_args, "parse": _aircrack_parse},
}


def _execute(cmd: list[str], on_line) -> str:
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    buffer: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        buffer.append(line)
        if on_line:
            on_line(line)
    proc.wait()
    return "".join(buffer)


def run(tool: str, inputs: dict, on_line=None) -> dict:
    """Run a tool against the given inputs; returns {found, entries, kind, tool}."""
    profile = _PROFILES.get(tool)
    if profile is None:
        raise TestToolError(f"Unknown tool '{tool}' (expected one of: {', '.join(TOOLS)})")
    if not shutil.which(tool):
        raise TestToolError(f"'{tool}' not found. Run 'oswg setup' to see how to install it.")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        text = _execute(profile["args"](inputs, tmpdir), on_line)
        post = profile.get("post")
        if post:
            text += "\n" + _execute(post(inputs, tmpdir), on_line)
        result = profile["parse"](text, tmpdir)
        result["tool"] = tool
        return result
