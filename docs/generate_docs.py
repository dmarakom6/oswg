#!/usr/bin/env python3
"""generate_docs.py - Regenerate the official OSWG documentation PDFs.

Produces two documents:

    docs/user-guide.pdf       - User Guide for OSWG
    docs/developer-guide.pdf  - Developer Guide for OSWG

The script is self-contained: it only depends on a PDF library. It prefers an
already-installed one (reportlab, fpdf2, weasyprint, pylatex). If none of
those is importable, it installs fpdf2 via pip and uses it. Rendering is
written against the fpdf2 API, so fpdf2 is always made importable before
building.

Usage (from the repository root):

    python docs/generate_docs.py                # uses VERSION = "0.7.0"
    python docs/generate_docs.py --version 0.8.0  # override the version

The version is embedded on each title page and in the footer of every page.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# The documented version. Override with: python docs/generate_docs.py --version X.Y.Z
VERSION = "0.7.0"

DOCS_DIR = Path(__file__).resolve().parent
USER_GUIDE_PATH = DOCS_DIR / "user-guide.pdf"
DEVELOPER_GUIDE_PATH = DOCS_DIR / "developer-guide.pdf"

# Supported PDF backends, in preference order (per the project requirement).
PDF_BACKENDS = (
    ("reportlab", "reportlab"),
    ("fpdf2", "fpdf"),
    ("weasyprint", "weasyprint"),
    ("pylatex", "pylatex"),
)

# Colors (RGB) matching OSWG's UI light theme (ui/src/routes/layout.css).
ACCENT = (99, 166, 122)        # --primary  #63A67A
ACCENT_DARK = (74, 128, 96)    # darker green for emphasis
ACCENT_SOFT = (231, 242, 235)  # light green tint for command boxes
INK = (26, 26, 26)             # --foreground #1A1A1A
GRAY = (102, 102, 102)         # --muted-foreground #666666
CODE_BG = (240, 240, 240)      # --muted #F0F0F0
CODE_BORDER = (224, 224, 224)  # --border #E0E0E0
TABLE_ALT = (240, 240, 240)    # --muted #F0F0F0
PAGE_BG = (250, 250, 250)      # --background #FAFAFA
WARNING = (217, 119, 6)        # --warning #D97706
NOTE_BG = (255, 247, 237)      # light warning tint for note boxes
WHITE = (255, 255, 255)


def _backend_available() -> str | None:
    """Return the label of the first installed supported PDF library."""
    for label, module in PDF_BACKENDS:
        if importlib.util.find_spec(module) is not None:
            return label
    return None


def resolve_backend() -> str:
    """Decide which PDF library to use.

    Returns the label of an installed backend, or installs fpdf2 via pip and
    returns "fpdf2" when no supported library is present. The renderer targets
    the fpdf2 API, so fpdf2 is guaranteed to be importable after this call.
    """
    available = _backend_available()
    if available == "fpdf2":
        return "fpdf2 (already installed)"
    if available is not None:
        # Another supported library is present, but the renderer in this
        # script targets fpdf2, so install it to guarantee a working build.
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "fpdf2"]
        )
        return f"fpdf2 (installed via pip; {available} also detected)"
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fpdf2"])
    return "fpdf2 (installed via pip)"


def _import_fpdf():
    """Import the fpdf2 classes used by the renderer."""
    from fpdf import FPDF
    from fpdf.fonts import FontFace

    return FPDF, FontFace


class _PdfDoc:
    """Thin wrapper around fpdf2.FPDF providing the document building blocks.

    Instantiated per document with the version, a document title (for the
    running header) and a short label (for the running footer).
    """

    def __init__(self, FPDF, version: str, doc_title: str, footer_label: str):
        self.version = version
        self.doc_title = doc_title
        self.footer_label = footer_label

        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.set_auto_page_break(auto=True, margin=20)
        self.pdf.set_margins(20, 18, 20)
        self.pdf.set_line_width(0.2)
        self.pdf.set_text_color(*INK)
        self._font = "Helvetica"

    # -- header / footer ---------------------------------------------------
    def _header(self) -> None:
        if self.pdf.page_no() == 1:
            return
        self.pdf.set_y(9)
        self.pdf.set_font("Helvetica", "", 8)
        self.pdf.set_text_color(*GRAY)
        self.pdf.cell(
            self.pdf.w / 2,
            6,
            f"OSWG v{self.version}  |  {self.doc_title}",
            align="L",
        )
        self.pdf.cell(
            self.pdf.w / 2 - self.pdf.r_margin,
            6,
            "Oddly Specific Wordlist Generator",
            align="R",
        )
        self.pdf.set_draw_color(*CODE_BORDER)
        self.pdf.set_line_width(0.3)
        self.pdf.line(
            self.pdf.l_margin, 17.5, self.pdf.w - self.pdf.r_margin, 17.5
        )
        self.pdf.set_line_width(0.2)

    def _footer(self) -> None:
        # Version is embedded in the footer on every page, including page 1.
        self.pdf.set_y(-15)
        self.pdf.set_font("Helvetica", "", 8)
        self.pdf.set_text_color(*GRAY)
        self.pdf.set_draw_color(*CODE_BORDER)
        self.pdf.set_line_width(0.3)
        self.pdf.line(
            self.pdf.l_margin,
            self.pdf.h - 18,
            self.pdf.w - self.pdf.r_margin,
            self.pdf.h - 18,
        )
        self.pdf.set_line_width(0.2)
        self.pdf.cell(
            self.pdf.w / 2,
            8,
            f"OSWG v{self.version}  |  {self.footer_label}",
            align="L",
        )
        self.pdf.cell(
            self.pdf.w / 2 - self.pdf.r_margin,
            8,
            f"Page {self.pdf.page_no()} / {{nb}}",
            align="R",
        )

    # -- layout helpers ----------------------------------------------------
    def _ensure_space(self, needed_mm: float) -> None:
        if self.pdf.get_y() + needed_mm > self.pdf.h - 20:
            self.pdf.add_page()

    def title_page(
        self,
        project: str,
        subtitle: str,
        doc_kind: str,
        meta_lines: list[str],
    ) -> None:
        p = self.pdf
        p.add_page()
        # Page background + a green accent bar across the top.
        p.set_fill_color(*PAGE_BG)
        p.rect(0, 0, p.w, p.h, "F")
        p.set_fill_color(*ACCENT)
        p.rect(0, 0, p.w, 6, "F")
        # Project name.
        p.set_xy(p.l_margin, 26)
        p.set_text_color(*INK)
        p.set_font("Helvetica", "B", 33)
        p.cell(0, 14, project)
        # Subtitle.
        p.set_xy(p.l_margin, 45)
        p.set_font("Helvetica", "", 13)
        p.set_text_color(*GRAY)
        p.cell(0, 8, subtitle)
        # Version badge.
        badge_w, badge_h = 64, 10
        bx, by = p.w - p.r_margin - badge_w, 46
        p.set_fill_color(*ACCENT)
        p.rect(bx, by, badge_w, badge_h, "F")
        p.set_xy(bx, by)
        p.set_font("Helvetica", "B", 11.5)
        p.set_text_color(WHITE)
        p.cell(badge_w, badge_h, f"Version {self.version}", align="C")
        # Document kind.
        p.set_xy(p.l_margin, 120)
        p.set_text_color(*ACCENT_DARK)
        p.set_font("Helvetica", "B", 21)
        p.cell(0, 10, doc_kind)
        # Short rule under the kind.
        p.set_draw_color(*ACCENT)
        p.set_line_width(0.8)
        p.line(p.l_margin, 134, p.l_margin + 60, 134)
        p.set_line_width(0.2)
        # Metadata box.
        box_w = p.w - p.l_margin - p.r_margin
        box_h = 11 + len(meta_lines) * 7
        p.set_draw_color(*CODE_BORDER)
        p.set_fill_color(WHITE)
        p.rect(p.l_margin, 150, box_w, box_h, "DF")
        p.set_font("Helvetica", "", 9.5)
        p.set_text_color(*INK)
        for i, line in enumerate(meta_lines):
            p.set_xy(p.l_margin + 6, 154 + i * 7)
            p.cell(box_w - 12, 6, line)
        p.set_xy(p.l_margin, 150 + box_h + 10)
        p.set_font("Helvetica", "", 9)
        p.set_text_color(*GRAY)
        p.cell(0, 6, "Official documentation - generated from the repository.")
        p.set_y(150 + box_h + 22)
        # Standalone cover: content starts on the next page.
        p.add_page()

    # -- content helpers ---------------------------------------------------
    def section(self, label: str, title: str) -> None:
        self._ensure_space(30)
        p = self.pdf
        p.set_x(p.l_margin)
        p.ln(4)
        p.set_font("Helvetica", "B", 15)
        p.set_text_color(*ACCENT)
        p.cell(0, 8, f"{label}  {title}", new_x="LMARGIN", new_y="NEXT")
        y = p.get_y()
        p.set_draw_color(*ACCENT)
        p.set_line_width(0.7)
        p.line(p.l_margin, y + 1, p.l_margin + 46, y + 1)
        p.set_line_width(0.2)
        p.ln(3.5)

    def subsection(self, title: str) -> None:
        self._ensure_space(24)
        p = self.pdf
        p.set_x(p.l_margin)
        p.ln(2.5)
        p.set_font("Helvetica", "B", 12)
        p.set_text_color(*ACCENT)
        p.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        p.ln(1.5)

    def command(self, text: str) -> None:
        """A highlighted monospace command header."""
        p = self.pdf
        p.set_x(p.l_margin)
        p.ln(2)
        p.set_font("Courier", "B", 9.5)
        box_w = p.w - p.l_margin - p.r_margin
        char_w = p.get_string_width("M")
        max_chars = max(10, int(box_w // char_w) - 2)
        # Wrap at word boundaries when possible; hard-split leftover long words.
        lines: list[str] = []
        cur = ""
        for word in text.split(" "):
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= max_chars:
                cur += " " + word
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        final: list[str] = []
        for ln in lines:
            while len(ln) > max_chars:
                final.append(ln[:max_chars])
                ln = ln[max_chars:]
            final.append(ln)
        lines = final
        line_h = 5.4
        box_h = len(lines) * line_h + 4
        self._ensure_space(box_h + 6)
        y0 = p.get_y()
        p.set_fill_color(*ACCENT_SOFT)
        p.set_draw_color(*ACCENT)
        p.rect(p.l_margin, y0, box_w, box_h, "DF")
        p.set_font("Courier", "B", 9.5)
        p.set_text_color(*ACCENT_DARK)
        yy = y0 + 2
        for line in lines:
            p.set_xy(p.l_margin + 3, yy)
            p.cell(box_w - 6, line_h, line)
            yy += line_h
        p.set_y(yy + 1.5)

    def paragraph(self, text: str, size: float = 10.5) -> None:
        p = self.pdf
        p.set_x(p.l_margin)
        p.set_font("Helvetica", "", size)
        p.set_text_color(*INK)
        p.multi_cell(0, 5.2, text, align="J")
        p.ln(1.5)

    def rich_paragraph(self, text: str, size: float = 10.5) -> None:
        """Paragraph with **bold** and `mono` inline markup."""
        p = self.pdf
        p.set_x(p.l_margin)
        p.set_font("Helvetica", "", size)
        p.set_text_color(*INK)
        self._write_rich(text, size)
        p.ln(1.5)

    def _write_rich(self, text: str, size: float) -> None:
        p = self.pdf
        parts = re.split(r"(\*\*.+?\*\*|`[^`]+`)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                p.set_font("Helvetica", "B", size)
                p.write(5.2, part[2:-2])
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                p.set_font("Courier", "", size - 0.5)
                p.write(5.2, part[1:-1])
            else:
                p.set_font("Helvetica", "", size)
                p.write(5.2, part)
        p.set_font("Helvetica", "", size)

    def bullets(self, items: list[str], size: float = 10.5) -> None:
        p = self.pdf
        p.set_x(p.l_margin)
        p.set_font("Helvetica", "", size)
        p.set_text_color(*INK)
        bullet_w = 6
        body_w = p.w - p.l_margin - p.r_margin - bullet_w
        for item in items:
            self._ensure_space(12)
            p.set_x(p.l_margin)
            p.cell(bullet_w, 5.2, "-", new_x="RIGHT")
            p.multi_cell(body_w, 5.2, item, align="L")
        p.ln(1)

    def code_block(self, text: str, size: float = 9) -> None:
        p = self.pdf
        p.set_x(p.l_margin)
        pad = 3.0
        p.set_font("Courier", "", size)
        char_w = p.get_string_width("M")
        avail = p.w - p.l_margin - p.r_margin - 2 * pad
        max_chars = max(8, int(avail // char_w))
        lines: list[str] = []
        for raw in text.split("\n"):
            raw = raw.rstrip()
            while len(raw) > max_chars:
                lines.append(raw[:max_chars])
                raw = raw[max_chars:]
            lines.append(raw)
        line_h = 4.4
        total_h = len(lines) * line_h + 2 * pad
        self._ensure_space(min(total_h, 250))
        y0 = p.get_y()
        box_w = p.w - p.l_margin - p.r_margin
        p.set_fill_color(*CODE_BG)
        p.set_draw_color(*CODE_BORDER)
        p.rect(p.l_margin, y0, box_w, total_h, "DF")
        p.set_font("Courier", "", size)
        p.set_text_color(*INK)
        yy = y0 + pad
        for line in lines:
            p.set_xy(p.l_margin + pad, yy)
            p.cell(box_w - 2 * pad, line_h, line)
            yy += line_h
        p.set_y(yy + 2)

    def make_table(
            self,
            headers: list[str],
            rows: list[list[str]],
            col_widths: list[float] | None = None,
            size: float = 9,
        ) -> None:
            """Hand-rolled table (no fpdf2 `table()` API, which overlaps rows on page splits)."""
            p = self.pdf
            p.set_x(p.l_margin)
            line_h = 5.0
            pad = 1.6
            box_w = p.w - p.l_margin - p.r_margin
            ncols = len(headers)
            cw = list(col_widths) if col_widths else [1.0] * ncols
            total = sum(cw)
            cw = [w / total * box_w for w in cw]

            def wrap(text: str, width: float) -> list[str]:
                p.set_font("Helvetica", "", size)
                avail = max(10.0, width - 2 * pad)
                out: list[str] = []
                for raw in str(text).split("\n"):
                    cur = ""
                    for word in raw.split(" "):
                        if not cur:
                            cur = word
                        elif p.get_string_width((cur + " " + word).strip()) <= avail:
                            cur = (cur + " " + word).strip()
                        else:
                            out.append(cur)
                            cur = word
                        while p.get_string_width(cur) > avail and len(cur) > 1:
                            i = len(cur) - 1
                            while i > 1 and p.get_string_width(cur[:i]) > avail:
                                i -= 1
                            out.append(cur[:i])
                            cur = cur[i:]
                    if cur:
                        out.append(cur)
                return out or [""]

            def row_height(cells: list[str]) -> float:
                h = 2 * pad
                for i, c in enumerate(cells):
                    h = max(h, len(wrap(c, cw[i])) * line_h + 2 * pad)
                return h

            def draw_row(cells: list[str], fill, bold: bool, text_color, size_pt: float) -> None:
                y0 = p.get_y()
                rh = row_height(cells)
                if y0 + rh > p.h - 20 and rh < p.h - 44:
                    p.add_page()
                    y0 = p.get_y()
                    draw_row(headers, ACCENT, True, WHITE, size)
                    y0 = p.get_y()
                p.set_fill_color(*fill)
                p.rect(p.l_margin, y0, box_w, rh, "F")
                x = p.l_margin
                p.set_font("Helvetica", "B" if bold else "", size_pt)
                p.set_text_color(*text_color)
                for i, c in enumerate(cells):
                    for j, ln in enumerate(wrap(c, cw[i])):
                        p.set_xy(x + pad, y0 + pad + j * line_h)
                        p.cell(cw[i] - 2 * pad, line_h, ln)
                    x += cw[i]
                p.set_y(y0 + rh)
                p.set_text_color(*INK)

            draw_row(headers, ACCENT, True, WHITE, size)
            for idx, row in enumerate(rows):
                draw_row(row, TABLE_ALT if idx % 2 == 1 else WHITE, False, INK, size)
            p.ln(2)

    def note(self, text: str) -> None:
        p = self.pdf
        p.set_x(p.l_margin)
        self._ensure_space(16)
        y0 = p.get_y()
        box_w = p.w - p.l_margin - p.r_margin
        lines = text.split("\n")
        box_h = 8 + len(lines) * 5.2
        p.set_fill_color(*NOTE_BG)
        p.set_draw_color(*WARNING)
        p.rect(p.l_margin, y0, box_w, box_h, "DF")
        p.set_font("Helvetica", "", 9.5)
        p.set_text_color(*INK)
        p.set_xy(p.l_margin + 4, y0 + 2)
        for line in lines:
            p.multi_cell(box_w - 8, 5.2, line, align="L")
            p.set_x(p.l_margin + 4)
        p.ln(2)

    def page_break(self) -> None:
        self.pdf.add_page()

    def save(self, path: Path) -> None:
        # Deterministic timestamp (midnight today) so same-day re-runs are
        # byte-identical; the human-readable date lives on the title page.
        from datetime import datetime, time

        stamp = datetime.combine(date.today(), time.min)
        self.pdf.set_creation_date(stamp)
        self.pdf.alias_nb_pages()
        self.pdf.output(str(path))


def _meta_lines(version: str) -> list[str]:
    today = date.today().strftime("%B %d, %Y")
    return [
        "Repository:   https://github.com/dmarakom6/oswg",
        f"Version:      {version}",
        "License:      MIT",
        "Homebrew tap: dmarakom6/homebrew-oswg",
        "Docker image: ghcr.io/dmarakom6/oswg",
        f"Generated:    {today}",
    ]


# ---------------------------------------------------------------------------
# User Guide content
# ---------------------------------------------------------------------------

def _build_user_guide(version: str, out_path: Path) -> None:
    FPDF, _ = _import_fpdf()

    class UserGuide(_PdfDoc):
        pass

    doc = UserGuide(FPDF, version, "User Guide", "User Guide")
    pdf = doc.pdf
    pdf.header = doc._header
    pdf.footer = doc._footer

    doc.title_page(
        "OSWG",
        "Oddly Specific Wordlist Generator",
        "User Guide",
        _meta_lines(version),
    )

    # 1. Introduction ------------------------------------------------------
    doc.section("1", "Introduction")
    doc.rich_paragraph(
        "OSWG (Oddly Specific Wordlist Generator) builds **targeted wordlists** from a "
        "website's own content. Instead of shipping a generic dictionary, it crawls the "
        "site you give it, extracts the words that actually matter - **keywords**, "
        "**usernames**, and **email addresses** - and applies a mutation engine that "
        "expands them into thousands of realistic guesses: leetspeak variants, case "
        "changes, number suffixes, special characters, and random combinations."
    )
    doc.rich_paragraph(
        "OSWG is a Python CLI plus a SvelteKit **web dashboard** in a single package. "
        "The dashboard mirrors the CLI (`oswg ui`) and adds real-time progress, "
        "visualizations, and saved templates. A `test` command drives external crackers "
        "(hashcat, john, hydra, medusa, ncrack, gobuster, aircrack-ng) against your "
        "generated wordlist, so you can measure how well it performs before you deploy it."
    )
    doc.subsection("What OSWG does")
    doc.bullets(
        [
            "Crawl - a polite crawler follows links (or sitemap.xml) and collects page text, titles, and metadata.",
            "Extract - keywords, email addresses, and usernames are pulled from the scraped content.",
            "Mutate - the mutation engine applies leet-speak, case, number-suffix, and special-character transforms.",
            "Generate - mutations are deduplicated, filtered, and trimmed to a target wordlist size.",
            "Dashboard - the web UI runs the same engine with live progress and visualizations.",
            "Test - external crackers are run against the finished wordlist and hits are summarized.",
        ]
    )

    # 2. Installation -------------------------------------------------------
    doc.section("2", "Installation")
    doc.rich_paragraph(
        "OSWG can be installed with pip, as a prebuilt binary, via Homebrew, from a "
        "`.deb` package, or run as a Docker image. All install methods produce the same "
        "`oswg` command."
    )

    doc.subsection("2.1  pip")
    doc.code_block("pip install oswg")
    doc.rich_paragraph(
        "Optional extras are installed with extras syntax: `oswg[auth]` adds NTLM HTTP "
        "authentication support, and `oswg[js]` adds JavaScript rendering via Playwright."
    )
    doc.code_block("pip install 'oswg[auth]'\npip install 'oswg[js]'")
    doc.rich_paragraph(
        "After installation, `oswg setup` reports which optional components are missing "
        "and offers to install them interactively. Pass `--check` to only report status "
        "without changing anything."
    )
    doc.code_block(
        "oswg setup          # show missing extras, install interactively\n"
        "oswg setup --check  # status only, install nothing"
    )

    doc.subsection("2.2  Prebuilt binaries (GitHub Releases)")
    doc.rich_paragraph(
        "Each GitHub Release ships single-file, dependency-free binaries for three "
        "platforms. Download the right one from "
        "`https://github.com/dmarakom6/oswg/releases`, make it executable, and run it "
        "directly - no Python or Node.js required."
    )
    doc.make_table(
        ["Platform", "Binary"],
        [
            ["Linux x86_64", "oswg-linux-x86_64"],
            ["macOS x86_64", "oswg-macos-x86_64"],
            ["macOS Apple Silicon (arm64)", "oswg-macos-arm64"],
        ],
        col_widths=[62, 108],
    )
    doc.code_block("chmod +x oswg-linux-x86_64\n./oswg-linux-x86_64 ui")

    doc.subsection("2.3  Debian / Ubuntu (.deb)")
    doc.rich_paragraph(
        "Download `oswg_<version>_amd64.deb` from the latest release and install it with "
        "apt. The package installs the `oswg` binary to `/usr/bin/oswg` and registers it "
        "with dpkg."
    )
    doc.code_block("sudo apt install ./oswg_0.7.0_amd64.deb")
    doc.rich_paragraph("To remove it:")
    doc.code_block("sudo apt remove oswg")

    doc.subsection("2.4  Homebrew (macOS)")
    doc.rich_paragraph(
        "OSWG is published through a personal tap. Add the tap, then install the formula:"
    )
    doc.code_block("brew tap dmarakom6/oswg\nbrew install oswg")

    doc.subsection("2.5  Docker (self-hosted UI)")
    doc.rich_paragraph(
        "For a self-hosted dashboard, run the published image. It bundles Chromium, so "
        "JavaScript rendering works out of the box - no `oswg setup` needed. Jobs, "
        "templates, and generated wordlists persist in the `oswg-data` volume."
    )
    doc.code_block(
        "docker run -d --name oswg -p 8000:8000 -v oswg-data:/data ghcr.io/dmarakom6/oswg"
    )
    doc.rich_paragraph(
        "Cracking tools used by `oswg test` stay **host-side**: the container runs the CLI "
        "and dashboard, while hashcat, John, hydra, and friends run on your own machine "
        "against targets you point it at."
    )

    # 3. CLI reference ------------------------------------------------------
    doc.section("3", "CLI reference")
    doc.rich_paragraph(
        "All functionality is exposed through a single `oswg` binary. Run `oswg --help` "
        "for the full command list and `oswg <command> --help` for per-command flags. "
        "Every command prints a human-readable summary with rich formatting."
    )

    doc.subsection("3.1  generate - build a wordlist")
    doc.command("oswg generate <url>")
    doc.rich_paragraph(
        "Crawls the target, extracts keywords, and applies the mutation engine to produce "
        "a wordlist. Accepts one or more seed URLs."
    )
    doc.make_table(
        ["Flag", "Meaning"],
        [
            ["--preset quick|standard|aggressive|extreme", "Apply a built-in preset (wordlist size plus advanced options)."],
            ["--template <name>", "Load a saved template as the base configuration."],
            ["--sitemap", "Discover pages from sitemap.xml."],
            ["--js-render", "Render pages with a real browser (requires oswg[js])."],
            ["--emails", "Include email addresses found on the target."],
            ["--username", "Extract usernames to a sidecar file (never merged in)."],
            ["--ai-completions", "Expand base words with AI - Ollama locally, or OpenAI with OPENAI_API_KEY."],
            ["--output, -o <file>", "Output path (default: wordlist.txt)."],
            ["--format txt|json|csv", "Output format; inferred from the file extension."],
            ["--gzip / --no-gzip", "Gzip-compress the output."],
            ["--dry-run", "Preview the wordlist without writing a file."],
            ["--merge <file>", "Merge an external wordlist file (repeatable)."],
            ["--merge-builtin", "Merge bundled common passwords."],
            ["--merge-rockyou", "Merge /usr/share/wordlists/rockyou.txt(.gz) if present."],
            ["--leet-level 1|2", "Leet-speak intensity (1 = basic, 2 = advanced)."],
            ["--random-combine", "Bind random pairs of base words (e.g. NutellaCream2024)."],
            ["--combine-count <n>", "Number of random combinations (default: 1000)."],
        ],
        col_widths=[62, 108],
    )
    doc.code_block(
        "oswg generate https://example.com --preset aggressive --emails -o example.txt"
    )

    doc.subsection("3.2  scrape - extract keywords")
    doc.command("oswg scrape <url>")
    doc.rich_paragraph(
        "Extracts keywords from a target without generating a wordlist - useful for recon "
        "before building a custom list. Output is printed as a preview or saved with `-o`."
    )
    doc.make_table(
        ["Flag", "Meaning"],
        [
            ["--output, -o <file>", "Save keywords to a file (preview on stdout if omitted)."],
            ["--sitemap", "Use sitemap.xml for page discovery."],
            ["--js-render", "Render pages with a real browser."],
            ["--emails", "Include email addresses found on the target."],
            ["--username", "Extract usernames to a sidecar file."],
            ["--rate-limit <sec>", "Delay between requests in seconds."],
            ["--jitter", "Randomize the delay by +/- 50% (with --rate-limit)."],
            ["--respect-robots", "Honor robots.txt rules."],
            ["--user-agent <ua>", "Custom User-Agent header for requests."],
        ],
        col_widths=[62, 108],
    )
    doc.code_block("oswg scrape https://example.com --emails --rate-limit 1 -o keywords.txt")

    doc.subsection("3.3  mutate - apply the mutation engine")
    doc.command("oswg mutate <file>")
    doc.rich_paragraph(
        "Applies the same mutation engine used by `generate` to an existing word file "
        "(one word per line) or to words passed directly on the command line."
    )
    doc.code_block("oswg mutate base-words.txt --leet-level 2 --special -o mutations.txt")
    doc.rich_paragraph(
        "Shared mutation flags include `--leet-level`, `--no-leet`, `--no-numbers`, "
        "`--special`, `--append`, `--prepend`, `--case-permutations`, and "
        "`--random-combine`."
    )

    doc.subsection("3.4  test - drive an external cracker")
    doc.command("oswg test <wordlist> --tool <tool>")
    doc.rich_paragraph(
        "Runs an external cracking tool against the wordlist and summarizes any hits. The "
        "tool itself must be installed; `oswg setup` reports which test tools are present."
    )
    doc.make_table(
        ["Tool", "Key flags", "Use case"],
        [
            ["hashcat", "--hashes <file>, --mode <num>", "Crack a hash file (mode 0 = MD5, 1000 = NTLM)."],
            ["john", "--hashes <file>", "Crack a hash file with John the Ripper."],
            ["hydra", "--url, --users, --passwords", "Online login brute force."],
            ["medusa", "--url, --users, --passwords", "Online login brute force."],
            ["ncrack", "--url, --users, --passwords", "Network authentication cracking."],
            ["gobuster", "--url", "Directory and file brute force."],
            ["aircrack", "--capture <pcap>", "Crack a Wi-Fi capture with aircrack-ng."],
        ],
        col_widths=[28, 72, 70],
    )
    doc.code_block(
        "oswg test wl.txt --tool hashcat --hashes hashes.txt --mode 0\n"
        "oswg test paths.txt --tool gobuster --url http://127.0.0.1:9202/"
    )

    doc.subsection("3.5  template - manage saved job templates")
    doc.command(
        "oswg template list | save NAME --type generate|scrape "
        "[--from-job <job_id> | --config-file <file>] | delete NAME"
    )
    doc.rich_paragraph(
        "Manage saved job templates so a good configuration can be reused."
    )
    doc.bullets(
        [
            "`oswg template list` - list saved templates with their type and creation time.",
            "`oswg template save NAME --type generate --from-job <job_id>` - save a completed job's configuration.",
            "`oswg template save NAME --type scrape --config-file <file>` - save from a JSON config file.",
            "`oswg template delete NAME` - remove a saved template.",
        ]
    )
    doc.code_block(
        "oswg template save intranet-audit --type generate --from-job 8f6c2a1e-...\n"
        "oswg template list\n"
        "oswg template delete intranet-audit"
    )

    doc.subsection("3.6  jobs - list recent jobs")
    doc.command("oswg jobs")
    doc.rich_paragraph(
        "Lists recent jobs with their ID, type, status, and target URL - useful when you "
        "missed a job ID in the output of `generate` or `scrape`."
    )

    doc.subsection("3.7  login - capture a browser session")
    doc.command("oswg login <url>")
    doc.rich_paragraph(
        "Opens an interactive browser so you can log in to a site, then captures the "
        "authenticated session (a Playwright storage-state JSON) for reuse with "
        "`--session-file` on `generate` and `scrape`."
    )

    doc.subsection("3.8  ui - launch the web dashboard")
    doc.command("oswg ui")
    doc.rich_paragraph(
        "Starts the FastAPI backend and opens the web dashboard in your browser at "
        "`http://127.0.0.1:8000` (the port auto-increments when busy)."
    )
    doc.make_table(
        ["Flag", "Meaning"],
        [
            ["--host <addr>", "Bind address (default: 127.0.0.1)."],
            ["--port <num>", "Base port (default: 8000)."],
            ["--no-browser", "Do not open the browser automatically."],
        ],
        col_widths=[62, 108],
    )
    doc.code_block("oswg ui\noswg ui --host 0.0.0.0 --port 8080 --no-browser")

    doc.subsection("3.9  Job IDs")
    doc.rich_paragraph(
        "`oswg generate` and `oswg scrape` persist every run as a **job** and print its "
        "identifier when the run finishes:"
    )
    doc.code_block("Job ID: 8f6c2a1e-3b4d-4e5f-9a0b-1c2d3e4f5a6b")
    doc.rich_paragraph(
        "Use that ID to snapshot a real run as a reusable template:"
    )
    doc.code_block("oswg template save intranet-audit --type generate --from-job 8f6c2a1e-3b4d-4e5f-9a0b-1c2d3e4f5a6b")
    doc.rich_paragraph(
        "If you missed the ID, `oswg jobs` lists the most recent runs."
    )

    # 4. Web dashboard ------------------------------------------------------
    doc.section("4", "Web dashboard")
    doc.rich_paragraph(
        "`oswg ui` opens the dashboard with four tabs - **Generate**, **Scrape**, "
        "**Mutate**, and **Test** - mirroring the CLI commands. Each tab collects a form; "
        "submissions stream progress in real time over a WebSocket and appear in the job "
        "history."
    )

    doc.subsection("4.1  Templates and presets")
    doc.rich_paragraph(
        "Below the URL field sits a collapsed **Templates & Presets** section:"
    )
    doc.bullets(
        [
            "Presets (quick, standard, aggressive, extreme) set both the target wordlist size and the advanced options - leet level, special characters, random combinations, merges, and minimum/maximum word length.",
            "Applying a preset or a saved template disables the other dropdown, so the two cannot conflict.",
            "Saved templates are also created from the **Save** button next to **Visualize** on any completed job.",
            "**Clear all** deletes every saved template in one click.",
        ]
    )

    doc.subsection("4.2  Visualizations")
    doc.rich_paragraph("Completed jobs can be explored with four visualizations:")
    doc.bullets(
        [
            "Coverage map - a sunburst chart of the crawled site structure.",
            "Keyword cloud - the extracted keywords sized by frequency.",
            "Frequency chart - the word-frequency distribution of the generated list.",
            "Mutation tree - how each base word expanded into its mutations.",
        ]
    )

    doc.subsection("4.3  Notifications and keyboard shortcuts")
    doc.bullets(
        [
            "Browser notifications - enable the bell toggle to be notified when a job completes.",
            "Keys 1-4 switch tabs, and `/` focuses the URL field.",
            "`?` opens the shortcuts help overlay.",
            "mod+Enter (Ctrl/Cmd+Enter) runs the current form.",
        ]
    )

    doc.subsection("4.4  Data location")
    doc.rich_paragraph(
        "OSWG follows the XDG Base Directory Specification. Jobs, templates, and generated "
        "wordlists live in `~/.local/share/oswg`. Override with the `XDG_DATA_HOME` or "
        "`OSWG_DATA_DIR` environment variables."
    )

    # 5. Worked examples ----------------------------------------------------
    doc.section("5", "Worked examples")

    doc.subsection("5.1  Gobuster directory brute force")
    doc.rich_paragraph(
        "A local site is served at `http://127.0.0.1:9202/` and exposes pages like "
        "`/index.html` and `/p2.html`, both answering HTTP 200. Generate a small "
        "path-focused wordlist from the site, then run gobuster against it:"
    )
    doc.code_block(
        "oswg generate http://127.0.0.1:9202/ --preset quick -o paths.txt\n"
        "oswg test paths.txt --tool gobuster --url http://127.0.0.1:9202/"
    )
    doc.rich_paragraph(
        "gobuster discovers the two live pages; the result table lists each path and its "
        "HTTP status:"
    )
    doc.make_table(
        ["Path", "Status"],
        [
            ["/index.html", "200"],
            ["/p2.html", "200"],
        ],
        col_widths=[60, 40],
    )

    doc.subsection("5.2  Hashcat MD5 crack")
    doc.rich_paragraph(
        "A wordlist `wl.txt` contains the word `password`, and a hashes file `hashes.txt` "
        "contains the MD5 digest `5f4dcc3b5aa765d61d8327deb882cf99` (the MD5 of "
        "`password`). Crack it with hashcat in mode 0:"
    )
    doc.code_block(
        "oswg test wl.txt --tool hashcat --hashes hashes.txt --mode 0"
    )
    doc.rich_paragraph(
        "hashcat recovers the plaintext, and the summary table shows the hash with its "
        "password:"
    )
    doc.make_table(
        ["Hash", "Password"],
        [
            ["5f4dcc3b5aa765d61d8327deb882cf99", "password"],
        ],
        col_widths=[100, 40],
    )

    doc.note(
        "These examples are for authorized testing only. Run OSWG and the external "
        "crackers only against systems you own or have explicit permission to test."
    )

    doc.save(out_path)


# ---------------------------------------------------------------------------
# Developer Guide content
# ---------------------------------------------------------------------------

def _build_developer_guide(version: str, out_path: Path) -> None:
    FPDF, _ = _import_fpdf()

    class DeveloperGuide(_PdfDoc):
        pass

    doc = DeveloperGuide(FPDF, version, "Developer Guide", "Developer Guide")
    pdf = doc.pdf
    pdf.header = doc._header
    pdf.footer = doc._footer

    doc.title_page(
        "OSWG",
        "Oddly Specific Wordlist Generator",
        "Developer Guide",
        _meta_lines(version),
    )

    # 1. Architecture -------------------------------------------------------
    doc.section("1", "Architecture")
    doc.rich_paragraph(
        "OSWG is a single Python package with an embedded web front end. A **FastAPI** "
        "application in `src/oswg/` provides the REST API, serves the pre-built "
        "**SvelteKit** dashboard from `src/oswg/static`, and runs every job as an async "
        "task with **WebSocket** progress updates. Scraping uses `httpx` and BeautifulSoup; "
        "**JavaScript rendering**, interactive login, and session capture are delegated to "
        "**Playwright**. Jobs and saved templates are stored in a **SQLite** database "
        "accessed through `aiosqlite`."
    )
    doc.make_table(
        ["Component", "Role"],
        [
            ["FastAPI backend (src/oswg/)", "REST endpoints, job orchestration, WebSocket updates."],
            ["SvelteKit UI (ui/)", "Dashboard; the production build is copied into src/oswg/static and served by the backend."],
            ["SQLite store", "Jobs and templates persisted via aiosqlite."],
            ["WebSocket", "Real-time job progress pushed to the dashboard."],
            ["Playwright", "JS rendering, interactive login, session capture."],
        ],
        col_widths=[56, 114],
    )
    doc.subsection("1.1  Repository layout")
    doc.code_block(
        "oswg/\n"
        "|-- src/oswg/\n"
        "|   |-- __init__.py       package version\n"
        "|   |-- cli.py            Typer CLI: generate, scrape, mutate, test, ...\n"
        "|   |-- launcher.py       uvicorn launcher for `oswg ui`\n"
        "|   |-- database.py       SQLite job/template store\n"
        "|   |-- models.py         Pydantic request/response models\n"
        "|   |-- config.py         settings (XDG data dir, retention)\n"
        "|   |-- core/\n"
        "|   |   |-- scraper.py    crawler: httpx, robots, rate limit, JS\n"
        "|   |   |-- generator.py  wordlist generation pipeline\n"
        "|   |   |-- mutations.py  mutation engine\n"
        "|   |   |-- presets.py    quick/standard/aggressive/extreme\n"
        "|   |   |-- rulegen.py    jtr/hashcat rule emission\n"
        "|   |   |-- ai.py         Ollama/OpenAI completions\n"
        "|   |   |-- test_runner.py  external cracker drivers\n"
        "|   |   |-- session.py    Playwright login and sessions\n"
        "|   |   `-- emails.py, usernames.py, wordlists.py, ...\n"
        "|   |-- routers/          FastAPI routers (generate, scrape, jobs, ...)\n"
        "|   |-- services/         job manager, template store\n"
        "|   `-- static/           SvelteKit build output\n"
        "|-- ui/                   SvelteKit frontend source\n"
        "|-- tests/                pytest unit + e2e suites\n"
        "|-- build_binary.py       PyInstaller build helper\n"
        "|-- oswg.spec             PyInstaller spec\n"
        "|-- Makefile              build/dev/lint/test/hooks targets\n"
        "|-- pyproject.toml        packaging, ruff, pytest configuration\n"
        "`-- .github/workflows/    ci.yml, release.yml, release-binaries.yml"
    )

    # 2. Development setup --------------------------------------------------
    doc.section("2", "Development setup")
    doc.rich_paragraph(
        "Create a virtual environment, install the package in editable mode with the "
        "`dev` and `js` extras, and install the UI dependencies:"
    )
    doc.code_block(
        "python -m venv venv\n"
        "source venv/bin/activate\n"
        "pip install -e '.[dev,js]'\n"
        "cd ui\n"
        "npm ci\n"
        "cd .."
    )
    doc.rich_paragraph(
        "`make build` builds the SvelteKit front end and copies `ui/build` into "
        "`src/oswg/static`, which is what the backend serves. `make dev` runs the build and "
        "starts the local server:"
    )
    doc.code_block(
        "make build   # npm run build in ui/, then copy static assets\n"
        "make dev     # make build + python -m oswg ui"
    )
    doc.rich_paragraph(
        "`make build` is required before running the app or the E2E suite - the backend "
        "serves the dashboard from `src/oswg/static`, so an empty static directory means a "
        "blank UI."
    )

    # 3. Testing ------------------------------------------------------------
    doc.section("3", "Testing")
    doc.rich_paragraph(
        "The project uses ruff and svelte-check for linting, plus pytest for a unit suite "
        "and a Playwright E2E suite."
    )
    doc.make_table(
        ["Command", "What it runs"],
        [
            ["make lint", "ruff check src/ tests/ and npx svelte-check in ui/."],
            ["pytest -q", "The 125 unit tests; E2E tests are deselected by default (pytest addopts -m 'not e2e')."],
            ["pytest -m e2e", "The Playwright E2E suite in tests/e2e/, which boots the app plus a fixture site."],
            ["make hooks", "Enable the pre-push git hook (git config core.hooksPath .githooks)."],
        ],
        col_widths=[56, 114],
    )
    doc.rich_paragraph(
        "The E2E suite requires `make build` first (the backend serves the built UI) and "
        "Playwright Chromium installed (`playwright install chromium`). The pre-push hook "
        "(`.githooks/pre-push`) runs ruff, the unit tests, and svelte-check before every "
        "push."
    )

    # 4. CI/CD --------------------------------------------------------------
    doc.section("4", "CI/CD")
    doc.rich_paragraph(
        "Three GitHub Actions workflows automate testing, releasing, and publishing. "
        "`ci.yml` runs 3 jobs: backend (ruff + pytest), UI (svelte-check + build), "
        "and E2E (Playwright)."
    )
    doc.make_table(
        ["Workflow", "Trigger", "Jobs / outputs"],
        [
            ["ci.yml", "Every push and pull request", "backend (ruff + pytest unit), UI (svelte-check + build), E2E (Playwright)."],
            ["release.yml", "Push to master", "Test job, then python-semantic-release versions the package and tags vX.Y.Z."],
            ["release-binaries.yml", "v* tags (or workflow_dispatch)", "Binaries, PyPI, .deb, Homebrew bump, Docker image, GitHub Release."],
        ],
        col_widths=[52, 44, 74],
    )
    doc.rich_paragraph(
        "`release-binaries.yml` builds PyInstaller binaries for `linux-x86_64`, "
        "`macos-x86_64`, and `macos-arm64`; publishes the wheel and sdist to PyPI; builds "
        "a `.deb` and attaches it to the release; bumps the Homebrew formula in the "
        "`dmarakom6/homebrew-oswg` tap; and builds and pushes the multi-arch "
        "(`linux/amd64` and `linux/arm64`) Docker image to "
        "`ghcr.io/dmarakom6/oswg`."
    )

    # 5. Release flow -------------------------------------------------------
    doc.section("5", "Release flow")
    doc.rich_paragraph(
        "Releases are fully automated once a version is chosen:"
    )
    doc.bullets(
        [
            "Commit the version bump with a conventional commit: `chore(release): X.Y.Z`.",
            "Push to master. `release.yml` runs its test job, then semantic-release creates the `vX.Y.Z` tag.",
            "Pushing the `vX.Y.Z` tag triggers `release-binaries.yml`, which produces the binaries, the `.deb`, the PyPI package, the Homebrew bump, and the Docker image.",
            "The GitHub Release is created with the binaries and the `.deb` attached automatically.",
        ]
    )
    doc.make_table(
        ["Step", "Trigger", "Workflow", "Outputs"],
        [
            ["Version commit", "chore(release): X.Y.Z on master", "release.yml", "vX.Y.Z tag"],
            ["Tag build", "vX.Y.Z tag pushed", "release-binaries.yml", "binaries, .deb, PyPI, Homebrew, Docker"],
        ],
        col_widths=[34, 56, 34, 46],
    )

    doc.note(
        "The current documented version is 0.7.0. Version bumps flow through the "
        "semantic-release pipeline - never edit pyproject.toml or src/oswg/__init__.py "
        "by hand for a release."
    )

    doc.save(out_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_docs.py",
        description="Generate the OSWG user and developer guide PDFs.",
    )
    parser.add_argument(
        "--version",
        default=None,
        metavar="X.Y.Z",
        help=f"Override the documented version (default: {VERSION}).",
    )
    args = parser.parse_args(argv)

    version = args.version if args.version else VERSION
    backend = resolve_backend()

    print(f"[docs] PDF backend : {backend}")
    print(f"[docs] Version     : {version}")
    print(f"[docs] Output dir  : {DOCS_DIR}")

    _build_user_guide(version, USER_GUIDE_PATH)
    print(f"[docs] wrote {USER_GUIDE_PATH.name}")

    _build_developer_guide(version, DEVELOPER_GUIDE_PATH)
    print(f"[docs] wrote {DEVELOPER_GUIDE_PATH.name}")

    # Verification: files exist, non-empty, and start with the PDF header.
    ok = True
    for path in (USER_GUIDE_PATH, DEVELOPER_GUIDE_PATH):
        if not path.exists():
            print(f"[docs] FAIL: {path} was not created")
            ok = False
            continue
        size = path.stat().st_size
        head = path.read_bytes()[:5]
        valid = head == b"%PDF-"
        status = "OK" if valid else "INVALID"
        print(
            f"[docs] verify: {path.name:22s} {size:8d} bytes  "
            f"header={head.decode('latin-1')!r}  {status}"
        )
        if not valid:
            ok = False

    if not ok:
        print("[docs] one or more PDFs failed verification")
        return 1
    print("[docs] done - both PDFs are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
