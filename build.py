#!/usr/bin/env python3
"""Build the poetry site. Dates may be YYYY-MM or YYYY-MM-DD."""

import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POEMS = ROOT / "_poems"
SITE = ROOT / "_site"
TITLE = "我来时一声便是歌"
DATE_RE = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$")


def parse_poem(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SystemExit(f"{path.name} 缺少开头的 ---")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SystemExit(f"{path.name} 的 front matter 不完整")
    meta = {}
    for line in parts[1].strip().splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("\"'")
    if "title" not in meta or "date" not in meta:
        raise SystemExit(f"{path.name} 需要 title 和 date")
    meta["date"] = normalize_date(meta["date"], path.name)
    body = parts[2].lstrip("\n")
    return meta, body


def normalize_date(value, name):
    match = DATE_RE.fullmatch(value)
    if not match:
        raise SystemExit(f"{name} 的 date 要写成 2026-10 或 2026-11-06，现在是 {value}")
    year, month, day = match.groups()
    if not 1 <= int(month) <= 12:
        raise SystemExit(f"{name} 的月份无效：{value}")
    if day is not None and not 1 <= int(day) <= 31:
        raise SystemExit(f"{name} 的日期无效：{value}")
    return value


def sort_key(date):
    year, month, day = DATE_RE.fullmatch(date).groups()
    return (int(year), int(month), int(day or 0))


def display_date(date):
    return date.replace("-", ".")


def poem_html(body):
    blocks = []
    for stanza in re.split(r"\n\s*\n", body.strip()):
        lines = [html.escape(line) for line in stanza.splitlines() if line.strip()]
        if lines:
            blocks.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n".join(blocks)


def page(title, body, home=False):
    heading = f"{html.escape(title)} · {TITLE}" if not home else TITLE
    mark = "" if home else f'<p class="mark"><a href="/">{TITLE}</a></p>\n    '
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{heading}</title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <main>
    {mark}{body}
  </main>
</body>
</html>
"""


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    poems = []
    for path in sorted(POEMS.glob("*.md")):
        meta, body = parse_poem(path)
        poems.append({
            "title": meta["title"],
            "date": meta["date"],
            "slug": path.stem,
            "html": poem_html(body),
        })
    poems.sort(key=lambda poem: sort_key(poem["date"]), reverse=True)

    title_buttons = []
    stages = []
    for index, poem in enumerate(poems):
        slug = html.escape(poem["slug"], quote=True)
        title = html.escape(poem["title"])
        current = ' aria-current="true"' if index == 0 else ""
        selected = " is-selected" if index == 0 else ""
        title_buttons.append(
            f'<li><button type="button" data-slug="{slug}"{current}>{title}</button></li>'
        )
        stages.append(
            f'<article id="poem-{index}" data-slug="{slug}" class="{selected.strip()}">\n'
            f'  <h2 class="poem-title">{title}</h2>\n'
            f'  <time datetime="{poem["date"]}">{display_date(poem["date"])}</time>\n'
            f'  <div class="poem">{poem["html"]}</div>\n'
            "</article>"
        )
    home = (
        "<header>\n"
        f'  <h1 class="site-title"><a href="/">{TITLE}</a></h1>\n'
        "  <p class=\"site-note\">HustHeCheng</p>\n"
        "</header>\n"
        '<div class="reader">\n'
        f'  <ul class="titles">{"".join(title_buttons)}</ul>\n'
        f'  <div class="stage">{"".join(stages)}</div>\n'
        "</div>\n"
        """<script>
const buttons = document.querySelectorAll(".titles button");
const articles = document.querySelectorAll(".stage article");
function selectPoem(slug, updateHash) {
  const known = Array.from(articles).some((article) => article.dataset.slug === slug);
  if (!known) slug = articles[0] ? articles[0].dataset.slug : "";
  buttons.forEach((button) => {
    if (button.dataset.slug === slug) button.setAttribute("aria-current", "true");
    else button.removeAttribute("aria-current");
  });
  articles.forEach((article) => {
    article.classList.toggle("is-selected", article.dataset.slug === slug);
  });
  if (updateHash && slug) history.replaceState(null, "", "#" + encodeURIComponent(slug));
}
buttons.forEach((button) => {
  button.addEventListener("click", () => selectPoem(button.dataset.slug, true));
});
const initial = decodeURIComponent(location.hash.replace(/^#/, ""));
if (initial) selectPoem(initial, false);
</script>"""
    )
    (SITE).mkdir()
    (SITE / "index.html").write_text(page(TITLE, home, home=True), encoding="utf-8")
    shutil.copytree(ROOT / "assets", SITE / "assets")
    for poem in poems:
        folder = SITE / "poems" / poem["slug"]
        folder.mkdir(parents=True)
        body = (
            '<article class="poem-page">\n'
            f'  <h1 class="poem-title">{html.escape(poem["title"])}</h1>\n'
            f'  <time datetime="{poem["date"]}">{display_date(poem["date"])}</time>\n'
            f'  <div class="poem">{poem["html"]}</div>\n'
            "</article>"
        )
        (folder / "index.html").write_text(page(poem["title"], body), encoding="utf-8")


if __name__ == "__main__":
    main()
