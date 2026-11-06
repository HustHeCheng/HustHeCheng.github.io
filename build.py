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
            f'  <p class="when"><time datetime="{poem["date"]}">{display_date(poem["date"])}</time></p>\n'
            f'  <h2 class="poem-title">{title}</h2>\n'
            f'  <div class="poem">{poem["html"]}</div>\n'
            "</article>"
        )
    home = (
        "<header>\n"
        f'  <h1 class="site-title"><a href="/">{html.escape(TITLE)}</a></h1>\n'
        "</header>\n"
        '<div class="reader">\n'
        '  <div class="index">\n'
        '    <span class="guide" aria-hidden="true"></span>\n'
        f'    <ul class="titles">{"".join(title_buttons)}</ul>\n'
        "  </div>\n"
        f'  <div class="stage">{"".join(stages)}\n'
        '    <button type="button" class="next" hidden aria-label="下一首">\n'
        '      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v15M6 13l6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>\n'
        "    </button>\n"
        "  </div>\n"
        "</div>\n"
        """<script>
const buttons = Array.from(document.querySelectorAll(".titles button"));
const articles = Array.from(document.querySelectorAll(".stage article"));
const guide = document.querySelector(".guide");
const nextButton = document.querySelector(".next");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let pull = 0;
let lockUntil = 0;

function currentIndex() {
  return buttons.findIndex((button) => button.getAttribute("aria-current") === "true");
}
function placeGuide() {
  const current = document.querySelector(".titles button[aria-current='true']");
  const index = document.querySelector(".index");
  if (!guide || !current || !index) return;
  const top = current.getBoundingClientRect().top - index.getBoundingClientRect().top;
  guide.style.height = current.offsetHeight + "px";
  guide.style.transform = "translateY(" + top + "px)";
}
function syncNext() {
  const index = currentIndex();
  const upcoming = buttons[index + 1];
  if (!nextButton) return;
  if (!upcoming) {
    nextButton.hidden = true;
    return;
  }
  nextButton.hidden = false;
  nextButton.setAttribute("aria-label", "下一首 " + upcoming.textContent);
}
function selectPoem(slug, updateHash) {
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
  syncNext();
  requestAnimationFrame(placeGuide);
  if (updateHash && slug) history.replaceState(null, "", "#" + encodeURIComponent(slug));
}
function atTop() {
  return window.scrollY <= 8;
}
function atBottom() {
  return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 6;
}
function watchScroll() {
  document.documentElement.classList.toggle("is-scrolled", !atTop());
  requestAnimationFrame(placeGuide);
}
function goNext() {
  if (Date.now() < lockUntil) return;
  const upcoming = buttons[currentIndex() + 1];
  if (!upcoming) return;
  lockUntil = Date.now() + 700;
  pull = 0;
  nextButton.classList.remove("is-pulling");
  selectPoem(upcoming.dataset.slug, true);
  window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
}
buttons.forEach((button) => {
  button.addEventListener("click", () => {
    if (document.documentElement.classList.contains("is-scrolled") && button.getAttribute("aria-current") !== "true") return;
    selectPoem(button.dataset.slug, true);
  });
});
nextButton.addEventListener("click", goNext);
document.querySelector(".titles").addEventListener("transitionend", placeGuide);
window.addEventListener("scroll", watchScroll, { passive: true });
window.addEventListener("resize", placeGuide);
window.addEventListener("wheel", (event) => {
  if (reduceMotion || nextButton.hidden || !atBottom() || event.deltaY <= 0) {
    pull = 0;
    nextButton.classList.remove("is-pulling");
    return;
  }
  pull += event.deltaY;
  nextButton.classList.add("is-pulling");
  if (pull > 420) goNext();
}, { passive: true });
let touchStart = 0;
window.addEventListener("touchstart", (event) => {
  touchStart = event.touches[0].clientY;
}, { passive: true });
window.addEventListener("touchmove", (event) => {
  if (reduceMotion || nextButton.hidden || !atBottom()) return;
  const lifted = touchStart - event.touches[0].clientY;
  if (lifted > 180) goNext();
}, { passive: true });
const initial = decodeURIComponent(location.hash.replace(/^#/, ""));
if (initial) selectPoem(initial, false);
else syncNext();
watchScroll();
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
