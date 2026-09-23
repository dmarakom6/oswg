# OSWG - Oddly Specific Wordlist Generator

A tool that generates targeted wordlists by scraping websites and applying intelligent mutations. Designed for penetration testers and security researchers.

## Features

- **Scrape** websites for relevant keywords
- **Generate** wordlists with l33t speak, capitalization, numbers, and special character mutations
- **Mutate** existing wordlists with the same transformation rules
- **Web UI** with real-time progress via WebSocket
- **Single binary** — CLI and web dashboard in one executable
- **XDG-compliant** — data stored in `~/.local/share/oswg/`

## Installation

### Option 1: Download prebuilt binary (recommended)

Download the latest release for your platform from the [Releases page](https://github.com/yourusername/oswg/releases).

```bash
# Linux
wget https://github.com/yourusername/oswg/releases/latest/download/oswg-linux-x86_64
chmod +x oswg-linux-x86_64
./oswg-linux-x86_64 ui

# macOS
wget https://github.com/yourusername/oswg/releases/latest/download/oswg-macos-arm64
chmod +x oswg-macos-arm64
./oswg-macos-arm64 ui
```

### Option 2: Install via pip

```bash
pip install oswg
oswg ui
```

Optional extras (JS rendering, NTLM auth) can be installed interactively with:

```bash
oswg setup            # shows what's missing and offers to install it
oswg setup --check    # just report status
```

### Option 3: Homebrew (macOS)

```bash
brew tap dmarakom6/oswg
brew install oswg
```

### Option 4: apt (Debian/Ubuntu)

Download `oswg_<version>_amd64.deb` from the latest [Release](https://github.com/yourusername/oswg/releases) and install it:

```bash
sudo apt install ./oswg_0.6.0_amd64.deb
```

The `.deb` installs the `oswg` binary to `/usr/bin/oswg` and registers it with dpkg (`sudo apt remove oswg` uninstalls).

### Option 5: Docker (self-hosted UI)

The image bundles Chromium, so JS rendering works out of the box (no `oswg setup`):

```bash
docker run -d --name oswg -p 8000:8000 -v oswg-data:/data ghcr.io/dmarakom6/osgw
```

Or with compose:

```bash
docker compose up -d
```

Data (jobs, templates, wordlists) persists in the `oswg-data` volume. Note: `oswg test` cracking tools (hashcat/john/…) are not bundled — run those on your host.

## Usage

### CLI Mode

```bash
# Generate a wordlist
oswg generate https://example.com --size 50000 -o wordlist.txt

# Scrape keywords only
oswg scrape https://example.com --max-pages 5

# Mutate words
oswg mutate password admin login --numbers --special -o mutations.txt
oswg mutate --file words.txt -o mutations.txt

# Output formats (inferred from the -o extension, or set with --format)
oswg generate https://example.com -o wordlist.json   # JSON with metadata
oswg scrape https://example.com -o keywords.csv      # CSV
oswg generate https://example.com -o wordlist.txt.gz # gzip-compressed
oswg generate https://example.com -o wordlist.json --gzip  # any format + gzip

# Include email addresses found on the target in the wordlist
oswg generate https://example.com --emails -o wordlist.txt
oswg scrape https://example.com --emails

# Extract usernames to a separate sidecar list (never merged into the wordlist)
oswg generate https://example.com --username -o wordlist.txt   # -> wordlist.usernames.txt
oswg scrape https://example.com --username

# HTTP authentication (basic/digest built-in; ntlm needs 'pip install oswg[auth]')
# Composes with --cookie/--cookie-file/--session-file for sites that need both layers.
oswg generate https://intranet.example.com --auth-type basic --auth-user alice --auth-pass s3cret
oswg scrape https://intranet.example.com --auth-type digest --auth-user alice --auth-pass s3cret
```

### Health checks

When the API/dashboard is running, monitoring endpoints are available on the
same origin (no authentication):

```bash
curl http://127.0.0.1:8000/health        # liveness: status, version, uptime
curl http://127.0.0.1:8000/health/ready  # readiness: database + storage checks
```

`/health/ready` returns HTTP 503 with `"status": "unhealthy"` when the
database is unreachable or the storage directory is not writable.

### Web Dashboard

```bash
oswg ui
```

The dashboard will automatically open in your browser at `http://127.0.0.1:8000`. If port 8000 is busy, it will auto-increment to 8001, 8002, etc.

**Options:**
- `--port 8080` — Start at a custom port
- `--host 0.0.0.0` — Bind to all interfaces (use with caution)
- `--no-browser` — Don't open the browser automatically

## Data Location

OSWG follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html):

- **Data:** `~/.local/share/oswg/` (database, generated wordlists)
- **Config:** `~/.config/oswg/` (future use)
- **Cache:** `~/.cache/oswg/` (future use)

Override with environment variables:
- `XDG_DATA_HOME` — Change the data directory
- `OSWG_DATA_DIR` — Override the oswg-specific directory

## Development

### Build from source

```bash
git clone https://github.com/yourusername/oswg
cd oswg

# Install dependencies
pip install -e ".[dev]"

# Run CLI
oswg generate https://example.com

# Run web UI
oswg ui

# Build standalone binary
python build.py
# → dist/oswg
```

### Project Structure

```
oswg/
├── src/oswg/          # Unified Python package
│   ├── core/          # Scraping & mutation engine
│   ├── routers/       # FastAPI routes
│   ├── services/      # Job management, file management
│   ├── cli.py         # Typer CLI entry point
│   ├── launcher.py    # --ui launcher
│   └── static/        # SvelteKit build output
├── ui/                # SvelteKit source
├── tests/             # Test suite
├── build.py           # PyInstaller build script
├── oswg.spec          # PyInstaller spec
├── pyproject.toml     # Package configuration
└── .github/workflows/ # CI/CD
```

## License

MIT
