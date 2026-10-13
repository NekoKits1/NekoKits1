"""Updates the alt text of the stats image in README.md from data/stats.json.

Everything else in the README is left exactly as it is.
"""
import datetime
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
README = HERE.parent.parent / "README.md"
DATA = HERE / "data"


def stats_alt(d):
    since = datetime.date.fromisoformat(d["created_at"][:10])
    langs = sorted(d["languages"].items(), key=lambda kv: -kv[1])[:5]
    parts = [
        (f'{d["contributions_year"]} contributions in {d["year"]}, {d["contributions_all"]} all time'
         if "contributions_year" in d else
         f'{d["commits_year"]} commits in {d["year"]}, {d["commits_all"]} all time'),
        f'{d["prs"]} pull requests ({d["prs_merged"]} merged)',
        f'current streak {d["streak_current"]} days, longest {d["streak_longest"]} days',
        f'{d["followers"]} followers',
        f'member since {since:%B %Y}',
    ]
    text = "GitHub stats: " + "; ".join(parts) + ". Top languages: " + ", ".join(k for k, _ in langs) + "."
    return html.escape(text, quote=True)


def main():
    stats_file = DATA / "stats.json"
    if not stats_file.exists():
        print("no stats.json found, skipping README update")
        return

    stats = json.loads(stats_file.read_text())
    s = README.read_text()

    # Update header alt (optional — only if the README has a header.svg with an alt)
    s, n = re.subn(
        r'(<img src="\./assets/header\.svg"[^>]*?alt=")[^"]*(")',
        lambda m: m.group(1) + html.escape(
            f'NekoKits1 — Étudiante Ingénieure en Réseaux & Cybersécurité', quote=True
        ) + m.group(2),
        s,
    )

    README.write_text(s)
    print("README updated")


if __name__ == "__main__":
    main()
