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

    groups = []
    stages = []
    for index, poem in enumerate(poems):
        slug = html.escape(poem["slug"], quote=True)
        title = html.escape(poem["title"])
        year = poem["date"][:4]
        current = ' aria-current="true"' if index == 0 else ""
        selected = ' class="is-selected"' if index == 0 else ""
        if not groups or groups[-1][0] != year:
            groups.append((year, []))
        groups[-1][1].append(
            f'<li><button type="button" data-slug="{slug}" data-year="{year}"{current}>{title}</button></li>'
        )
        stages.append(
            f'<article id="poem-{index}" data-slug="{slug}"{selected}>\n'
            f'  <p class="when"><time datetime="{poem["date"]}">{display_date(poem["date"])}</time></p>\n'
            f'  <h2 class="poem-title">{title}</h2>\n'
            f'  <div class="poem">{poem["html"]}</div>\n'
            "</article>"
        )
    index_html = "".join(
        f'<section class="year"><h3>{year}<span>{len(items)}</span></h3>'
        f'<ul class="titles">{"".join(items)}</ul></section>'
        for year, items in groups
    )
    span = f"{groups[-1][0]} — {groups[0][0]}" if groups else ""
    first = html.escape(poems[0]["title"]) if poems else ""
    home = (
        "<header>\n"
        f'  <h1 class="site-title"><a href="/">{html.escape(TITLE)}</a></h1>\n'
        f'  <p class="tally">{len(poems)} 首 · {span}</p>\n'
        "</header>\n"
        '<div class="reader">\n'
        '  <nav class="index" aria-label="诗目">\n'
        '    <button type="button" class="toggle" aria-expanded="false">\n'
        f'      <span class="toggle-label">目录</span><span class="toggle-current">{first}</span>\n'
        '      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>\n'
        "    </button>\n"
        '    <div class="list">\n'
        '      <span class="guide" aria-hidden="true"></span>\n'
        f"      {index_html}\n"
        "    </div>\n"
        "  </nav>\n"
        f'  <div class="stage">{"".join(stages)}\n'
        '    <nav class="turn">\n'
        '      <button type="button" class="prev" hidden><span>上一首</span><b></b></button>\n'
        '      <button type="button" class="next" hidden><span>下一首</span><b></b>\n'
        '        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v15M6 13l6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>\n'
        "      </button>\n"
        "    </nav>\n"
        "  </div>\n"
        "</div>\n"
        """<script>
const buttons = Array.from(document.querySelectorAll(".titles button"));
const articles = Array.from(document.querySelectorAll(".stage article"));
const nav = document.querySelector(".index");
const list = document.querySelector(".index .list");
const guide = document.querySelector(".guide");
const toggle = document.querySelector(".toggle");
const toggleCurrent = document.querySelector(".toggle-current");
const nextButton = document.querySelector(".next");
const prevButton = document.querySelector(".prev");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let pull = 0;
let lockUntil = 0;

function currentIndex() {
  return buttons.findIndex((button) => button.getAttribute("aria-current") === "true");
}
function placeGuide() {
  const current = buttons[currentIndex()];
  if (!guide || !current) return;
  const top = current.getBoundingClientRect().top - list.getBoundingClientRect().top + list.scrollTop;
  guide.style.height = current.offsetHeight + "px";
  guide.style.transform = "translateY(" + top + "px)";
}
function revealCurrent(smooth) {
  const current = buttons[currentIndex()];
  if (!current || list.clientHeight === 0) return;
  const box = list.getBoundingClientRect();
  const item = current.getBoundingClientRect();
  const margin = 48;
  let delta = 0;
  if (item.top < box.top + margin) delta = item.top - box.top - margin;
  else if (item.bottom > box.bottom - margin) delta = item.bottom - box.bottom + margin;
  if (delta) list.scrollBy({ top: delta, behavior: smooth && !reduceMotion ? "smooth" : "auto" });
}
function fillTurn(button, target) {
  if (!target) {
    button.hidden = true;
    return;
  }
  button.hidden = false;
  button.querySelector("b").textContent = target.textContent;
  button.dataset.slug = target.dataset.slug;
}
function syncTurn() {
  const index = currentIndex();
  fillTurn(prevButton, buttons[index - 1]);
  fillTurn(nextButton, buttons[index + 1]);
}
function setOpen(open) {
  nav.classList.toggle("is-open", open);
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
  const current = buttons[currentIndex()];
  if (open && current) {
    list.scrollTop = current.getBoundingClientRect().top - list.getBoundingClientRect().top + list.scrollTop - 72;
  }
}
function selectPoem(slug, updateHash, smooth = true) {
  const known = articles.some((article) => article.dataset.slug === slug);
  if (!known) slug = articles[0] ? articles[0].dataset.slug : "";
  buttons.forEach((button) => {
    if (button.dataset.slug === slug) button.setAttribute("aria-current", "true");
    else button.removeAttribute("aria-current");
  });
  articles.forEach((article) => {
    const chosen = article.dataset.slug === slug;
    if (chosen) {
      article.classList.remove("is-selected");
      void article.offsetWidth;
    }
    article.classList.toggle("is-selected", chosen);
  });
  const current = buttons[currentIndex()];
  if (current) toggleCurrent.textContent = current.textContent;
  syncTurn();
  requestAnimationFrame(() => { placeGuide(); revealCurrent(smooth); });
  if (updateHash && slug) history.replaceState(null, "", "#" + encodeURIComponent(slug));
}
function atBottom() {
  return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 6;
}
function go(slug) {
  if (!slug || Date.now() < lockUntil) return;
  lockUntil = Date.now() + 700;
  pull = 0;
  nextButton.classList.remove("is-pulling");
  selectPoem(slug, true);
  window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
}
buttons.forEach((button) => {
  button.addEventListener("click", () => {
    setOpen(false);
    if (button.getAttribute("aria-current") === "true") return;
    selectPoem(button.dataset.slug, true);
    window.scrollTo({ top: 0, behavior: "auto" });
  });
});
toggle.addEventListener("click", () => setOpen(!nav.classList.contains("is-open")));
nextButton.addEventListener("click", () => go(nextButton.dataset.slug));
prevButton.addEventListener("click", () => go(prevButton.dataset.slug));
document.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.key === "Escape") setOpen(false);
  if (event.key === "ArrowRight" && !nextButton.hidden) go(nextButton.dataset.slug);
  if (event.key === "ArrowLeft" && !prevButton.hidden) go(prevButton.dataset.slug);
});
window.addEventListener("scroll", () => {
  document.documentElement.classList.toggle("is-scrolled", window.scrollY > 8);
}, { passive: true });
window.addEventListener("resize", placeGuide);
window.addEventListener("wheel", (event) => {
  if (reduceMotion || nextButton.hidden || nav.classList.contains("is-open") || list.contains(event.target) || !atBottom() || event.deltaY <= 0) {
    pull = 0;
    nextButton.classList.remove("is-pulling");
    return;
  }
  pull += event.deltaY;
  nextButton.classList.add("is-pulling");
  if (pull > 420) go(nextButton.dataset.slug);
}, { passive: true });
const initial = decodeURIComponent(location.hash.replace(/^#/, ""));
if (initial) selectPoem(initial, false, false);
else syncTurn();
requestAnimationFrame(() => { placeGuide(); revealCurrent(false); });
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
            f'  <p class="when"><time datetime="{poem["date"]}">{display_date(poem["date"])}</time></p>\n'
            f'  <h1 class="poem-title">{html.escape(poem["title"])}</h1>\n'
            f'  <div class="poem">{poem["html"]}</div>\n'
            "</article>"
        )
        (folder / "index.html").write_text(page(poem["title"], body), encoding="utf-8")


if __name__ == "__main__":
    main()
