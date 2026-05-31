"""Export the bank to **GIFT** — Moodle's plain-text question-import format.

One `.gift` file per language, ready to drop into a Moodle question bank
(Import → GIFT). It is **self-contained**: figures are embedded as base64
`data:` URIs inside `[html]` question text, so there is no separate media step.
Questions are grouped into a `$CATEGORY` per exam theme, so a Moodle import lands
them in one subcategory per domain — the same domain-study shape as the Anki
subdecks. Standard library only; deterministic (sorted, no timestamps).

GIFT shape per question (single-answer uses `=`/`~`; multi-answer uses weighted
`~%50%` so the exam's "one or two correct" maps cleanly):

    $CATEGORY: Permis bateau (FR)/Signalisation

    ::q-id:: [html]<img …>Stem ? {
    =Right answer
    ~Wrong answer
    ####[html]Explanation — Source: ONI art. 16
    }

Escaping: the GIFT control characters `~ = # { } :` (and `\\`) are backslash-
escaped in every *content* fragment (stem, choices, feedback, even the embedded
HTML); Moodle restores them on import, so the data URIs and links survive intact.
The structural tokens (`::`, `{`, `}`, `=`, `~`, `####`) are written raw.
"""

from __future__ import annotations

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import themes                                  # noqa: E402
from src.questions import schema as qschema             # noqa: E402
from src.questions.schema import Question               # noqa: E402
from tools import anki                                  # noqa: E402  (shared helpers)

BASE = anki.BASE
DATA = anki.DATA
QDB_PATH = anki.QDB_PATH
OUT_DIR = os.path.join(DATA, "gift")

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".svg": "image/svg+xml"}


def _esc(text: str) -> str:
    """Backslash-escape the GIFT control characters; backslash first."""
    out = (text or "").replace("\\", "\\\\")
    for ch in "~=#{}:":
        out = out.replace(ch, "\\" + ch)
    return out


def _data_uri(img_path: str) -> str:
    abs_src = os.path.join(BASE, img_path)
    if not os.path.exists(abs_src):
        return ""
    mime = _MIME.get(os.path.splitext(abs_src)[1].lower(), "image/png")
    with open(abs_src, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return f'<img src="data:{mime};base64,{b64}" alt="">'


def _pct(k: int) -> str:
    """Per-correct-answer weight for a k-correct question, summing to 100%."""
    v = 100.0 / k
    return f"{v:.5f}".rstrip("0").rstrip(".")


def _answers(q: Question) -> list[str]:
    if len(q.correct) <= 1:                       # single answer: =right / ~wrong
        return [(("=" if c.is_correct else "~") + _esc(c.text)) for c in q.choices]
    pct = _pct(len(q.correct))                    # multi: weighted, wrongs at -100%
    return [(f"~%{pct}%" if c.is_correct else "~%-100%") + _esc(c.text)
            for c in q.choices]


def _feedback(q: Question) -> str:
    """General feedback shown after answering: explanation + a cited source link.
    The whole HTML is GIFT-escaped; Moodle restores it, so the link survives."""
    p = q.provenance
    cite = p.ref or p.source or ""
    if p.source and p.source != (p.ref or ""):
        cite = f"{cite} — {p.source}" if cite else p.source
    if p.as_of:
        cite += f" ({p.as_of})"
    src = ""
    if cite or p.url:
        link = f'<a href="{p.url}">{cite or p.url}</a>' if p.url else cite
        src = f"Source : {link}"
    pieces = [x for x in (q.explanation, src) if x]
    if not pieces:
        return ""
    return "####[html]" + _esc("<br>".join(pieces))


def _render(q: Question) -> str:
    img = _data_uri(q.image) if q.image else ""
    head = f"::{_esc(q.id)}:: [html]" + _esc(img) + _esc(q.stem) + " {"
    lines = [head] + _answers(q)
    fb = _feedback(q)
    if fb:
        lines.append(fb)
    lines.append("}")
    return "\n".join(lines)


def _write_gift(questions: list[Question], lang: str, out_path: str) -> None:
    top = f'{anki._L.get(lang, anki._L["fr"])["deck"]} ({lang.upper()})'
    order = list(themes.THEMES)
    qs = sorted(questions, key=lambda x: (order.index(x.theme) if x.theme in order
                                          else 99, x.id))
    out = ["// Boating-licence question bank — GIFT export for Moodle.",
           "// Self-contained: figures are embedded as base64 data URIs.", ""]
    current = None
    for q in qs:
        if q.theme != current:
            current = q.theme
            cat = f"{top}/{anki._theme_label(lang, q.theme)}"
            out.append(f"$CATEGORY: {cat}\n")
        out.append(_render(q))
        out.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def export_to(conn, out_dir: str, lang: str | None) -> int:
    """Write boating-licence[.lang].gift into out_dir; returns the question count.
    Used by `run.py web` so the player can offer the GIFT file as a download."""
    qs = anki._exportable(conn, lang)
    if not qs:
        return 0
    os.makedirs(out_dir, exist_ok=True)
    sfx = "" if lang is None else f".{lang}"
    _write_gift(qs, lang or "fr", os.path.join(out_dir, f"boating-licence{sfx}.gift"))
    return len(qs)


def cmd_export(args) -> None:
    if not os.path.exists(QDB_PATH):
        sys.exit("no question bank — run `python run.py questions` first")
    conn = qschema.connect(QDB_PATH)
    n = export_to(conn, OUT_DIR, args.lang)
    if not n:
        sys.exit(f"no exportable questions for lang={args.lang!r}")
    sfx = "" if args.lang is None else f".{args.lang}"
    print(f"✓ {os.path.join(OUT_DIR, f'boating-licence{sfx}.gift')}  ({n} questions)")
    conn.close()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="GIFT (Moodle) export for the bank")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help="write data/gift/boating-licence[.lang].gift")
    e.add_argument("lang", nargs="?", default=None,
                   help="content language (default: all, mixed bank)")
    args = ap.parse_args()
    {"export": cmd_export}[args.cmd](args)


if __name__ == "__main__":
    main()
