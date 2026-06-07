#!/usr/bin/env python3
"""Build Chenyi Freight static website.

SEO guide system v2:
- Keeps four focused landing clusters: USA, Europe, UK and Australia.
- Generates isolated guide pages by cluster.
- Adds guide cards only to the matching landing page.
- Creates a clean sitemap.xml and AI-friendly robots.txt.
- Replaces duplicate route folders with redirect pages.
- Consolidates older EU-country landing URLs into the Europe landing page.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import re
import html
import json
import datetime
import sys
import yaml
import mistune

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SITE_URL = "https://www.doorhc.com"
BUILD_DATE = datetime.date.today().isoformat()

EXCLUDE_TOP_LEVEL = {
    ".git", ".github", ".gitignore", ".pages.yml", "content", "data", "dist", "scripts", "templates",
    "requirements.txt", "UPLOAD_GUIDE_CN.txt", "V2_UPLOAD_STEPS_CN.txt", "CHANGE_SUMMARY.txt", "CHANGE_SUMMARY_V2_CN.txt",
    "CLOUDFLARE_301_REDIRECTS_CN.txt", "CLOUDFLARE_301_REDIRECTS.csv",
    "NEXT_COUNTRY_PAGE_TEMPLATE.txt", "README_DEPLOY.txt", "README_UPLOAD_STEPS.txt",
}
SITEMAP_ROOT_FILES = ["index.html", "services.html", "tracking.html", "about.html", "faq.html", "contact.html"]
markdown = mistune.create_markdown(escape=False, plugins=["table"])


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def load_markets():
    return {x["key"]: x for x in load_yaml(ROOT / "data" / "markets.yml")}


def load_redirects():
    return load_yaml(ROOT / "data" / "route_redirects.yml")


def parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"Missing YAML frontmatter: {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid YAML frontmatter: {path}")
    meta = yaml.safe_load(parts[1]) or {}
    return meta, parts[2].strip()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "guide"


def date_string(value, default=BUILD_DATE):
    if not value:
        return default
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)[:10]


def read_template(name: str):
    return (ROOT / "templates" / name).read_text(encoding="utf-8")


def replace_tokens(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def copy_source():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for p in ROOT.iterdir():
        if p.name in EXCLUDE_TOP_LEVEL or p.name.endswith(".bak"):
            continue
        target = DIST / p.name
        if p.is_dir():
            shutil.copytree(p, target)
        elif p.is_file():
            shutil.copy2(p, target)


def inject_before_head_close(path: Path, snippet: str, marker: str | None = None):
    text = path.read_text(encoding="utf-8")
    if marker and marker in text:
        return
    text = text.replace("</head>", snippet + "\n</head>", 1)
    path.write_text(text, encoding="utf-8")


def read_canonical(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', text, flags=re.I)
    return match.group(1) if match else None


def jsonld(data):
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=2) + "\n</script>"


def load_guides(markets):
    guides = []
    base = ROOT / "content" / "guides"
    for market, market_data in markets.items():
        market_dir = base / market
        if not market_dir.exists():
            continue
        for path in sorted(market_dir.glob("*.md")):
            meta, body = parse_frontmatter(path)
            if not bool(meta.get("published", False)):
                continue
            required = ["title", "description", "seo_title", "seo_description", "date"]
            missing = [field for field in required if not meta.get(field)]
            if missing:
                raise ValueError(f"{path}: missing fields {missing}")
            focus_country = str(meta.get("focus_country") or "").strip()
            slug = slugify(path.stem)
            url = f"/guides/{market}/{slug}.html"
            guides.append({
                "market": market,
                "market_label": market_data["label"],
                "focus_country": focus_country,
                "landing_page": "/" + market_data["landing_page"],
                "source": path,
                "slug": slug,
                "url": url,
                "title": str(meta["title"]).strip(),
                "description": str(meta["description"]).strip(),
                "seo_title": str(meta["seo_title"]).strip(),
                "seo_description": str(meta["seo_description"]).strip(),
                "date": date_string(meta.get("date")),
                "updated": date_string(meta.get("updated") or meta.get("date")),
                "featured": bool(meta.get("featured", False)),
                "body_html": markdown(body),
            })
    return guides


def sort_guides(items):
    return sorted(items, key=lambda x: (x["featured"], x["date"], x["title"]), reverse=True)


def guide_kicker(item):
    base = f'{item["market_label"]} shipping guide'
    focus = item.get("focus_country") or ""
    if focus and focus.lower() != "europe-wide":
        return base + " · " + focus
    return base


def guide_cards(items, limit=None):
    shown = items[:limit] if limit else items
    cards = []
    for item in shown:
        cards.append(f'''<article class="guide-card">
          <div class="guide-card-body">
            <span class="guide-kicker">{html.escape(guide_kicker(item))}</span>
            <h3><a href="{html.escape(item['url'])}">{html.escape(item['title'])}</a></h3>
            <p>{html.escape(item['description'])}</p>
            <a class="guide-read-more" href="{html.escape(item['url'])}">Read guide →</a>
          </div>
        </article>''')
    return "\n".join(cards)


def generate_guides(markets, guides):
    page_template = read_template("guide-page.html")
    index_template = read_template("guide-index.html")
    by_market = {key: [] for key in markets}
    for guide in guides:
        by_market[guide["market"]].append(guide)
    for key in by_market:
        by_market[key] = sort_guides(by_market[key])

    for guide in guides:
        related = [item for item in by_market[guide["market"]] if item["url"] != guide["url"]]
        related_html = guide_cards(related, 3) if related else '<p class="guide-empty">Need help with your shipment? Send your cargo details and delivery address for a route recommendation.</p>'
        article_schema = jsonld({
            "@context": "https://schema.org", "@type": "Article",
            "headline": guide["title"], "description": guide["description"],
            "datePublished": guide["date"], "dateModified": guide["updated"],
            "author": {"@type": "Person", "name": "Noah"},
            "publisher": {"@type": "Organization", "name": "Chenyi Freight", "legalName": "Yiwu Chenyi International Freight Agency Limited", "url": SITE_URL},
            "mainEntityOfPage": SITE_URL + guide["url"],
        })
        breadcrumb_schema = jsonld({
            "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": guide["market_label"] + " Shipping", "item": SITE_URL + guide["landing_page"]},
                {"@type": "ListItem", "position": 3, "name": guide["title"], "item": SITE_URL + guide["url"]},
            ],
        })
        output = replace_tokens(page_template, {
            "SEO_TITLE": html.escape(guide["seo_title"]),
            "SEO_DESCRIPTION": html.escape(guide["seo_description"]),
            "CANONICAL_URL": SITE_URL + guide["url"],
            "JSON_LD": article_schema + "\n" + breadcrumb_schema,
            "MARKET_LABEL": html.escape(guide["market_label"]),
            "MARKET_LANDING": html.escape(guide["landing_page"]),
            "TITLE": html.escape(guide["title"]),
            "DESCRIPTION": html.escape(guide["description"]),
            "DATE": html.escape(guide["date"]),
            "UPDATED": html.escape(guide["updated"]),
            "BODY_HTML": guide["body_html"],
            "RELATED_CARDS": related_html,
            "GUIDE_INDEX_URL": f'/guides/{guide["market"]}/',
        })
        out = DIST / guide["url"].lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")

    for market, items in by_market.items():
        if not items:
            continue
        market_data = markets[market]
        output = replace_tokens(index_template, {
            "MARKET_LABEL": html.escape(market_data["label"]),
            "MARKET_LANDING": "/" + market_data["landing_page"],
            "CANONICAL_URL": SITE_URL + f"/guides/{market}/",
            "GUIDE_CARDS": guide_cards(items),
        })
        out = DIST / "guides" / market / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")
    return by_market


def inject_organization():
    home = DIST / "index.html"
    schema = "<!-- organization-schema -->\n" + jsonld({
        "@context": "https://schema.org", "@type": "Organization",
        "name": "Chenyi Freight", "legalName": "Yiwu Chenyi International Freight Agency Limited",
        "url": SITE_URL + "/", "email": "inkovnoah@gmail.com", "telephone": "+86 195 6438 0551",
        "address": {"@type": "PostalAddress", "addressLocality": "Yiwu", "addressRegion": "Zhejiang", "addressCountry": "CN"},
    })
    inject_before_head_close(home, "\n  " + schema.replace("\n", "\n  "), "organization-schema")


def inject_route_enhancements(markets, by_market):
    for key, market in markets.items():
        path = DIST / market["landing_page"]
        if not path.exists():
            raise FileNotFoundError(f"Missing landing page: {path}")
        canonical = read_canonical(path) or SITE_URL + "/" + market["landing_page"]
        schema = "<!-- route-breadcrumb-schema -->\n" + jsonld({
            "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": market["label"] + " Shipping", "item": canonical},
            ],
        })
        inject_before_head_close(path, "\n  " + schema.replace("\n", "\n  "), "route-breadcrumb-schema")
        items = by_market.get(key) or []
        if not items:
            continue
        more_button = ""
        if len(items) > 4:
            more_button = f'<p class="guide-list-link"><a class="btn btn-ghost" href="/guides/{key}/">View more {html.escape(market["label"])} shipping guides</a></p>'
        section = f'''\n  <section class="bg guide-section" id="shippingGuides">
    <div class="container">
      <div class="section-head">
        <span class="mini-label">Practical shipping knowledge</span>
        <h2>{html.escape(market['label'])} shipping guides.</h2>
        <p>Browse practical answers about routes, cargo preparation and delivery planning for shipments from China to {html.escape(market['label'])}.</p>
      </div>
      <div class="guide-grid">
{guide_cards(items, 4)}
      </div>
      {more_button}
    </div>
  </section>\n\n'''
        text = path.read_text(encoding="utf-8")
        needle = '  <section class="quote-section" id="quoteForm">'
        if needle not in text:
            needle = "</main>"
        text = text.replace(needle, section + needle, 1)
        path.write_text(text, encoding="utf-8")


def redirect_html(target: str):
    return replace_tokens(read_template("redirect.html"), {"TARGET_URL": target, "FULL_TARGET_URL": SITE_URL + target})


def write_redirect_pages(markets, redirects):
    for market in markets.values():
        target = "/" + market["landing_page"]
        out = DIST / market["landing_page"].removesuffix(".html") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(redirect_html(target), encoding="utf-8")
    for item in redirects:
        source = item["source"]
        target = "/" + item["target"]
        root_out = DIST / source
        root_out.write_text(redirect_html(target), encoding="utf-8")
        alias_out = DIST / source.removesuffix(".html") / "index.html"
        alias_out.parent.mkdir(parents=True, exist_ok=True)
        alias_out.write_text(redirect_html(target), encoding="utf-8")


def write_robots():
    robots = '''User-agent: *
Allow: /

# OpenAI search and user-request access
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /

# Google Search and Gemini-related access
User-agent: Googlebot
Allow: /
User-agent: Google-Extended
Allow: /

# Claude search and user-request access
User-agent: Claude-SearchBot
Allow: /
User-agent: Claude-User
Allow: /

# Perplexity search and user-request access
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /

Sitemap: https://www.doorhc.com/sitemap.xml
'''
    (DIST / "robots.txt").write_text(robots, encoding="utf-8")


def file_lastmod(path: Path):
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def source_lastmod(filename: str):
    source = ROOT / filename
    return file_lastmod(source) if source.exists() else BUILD_DATE


def max_date(*values):
    valid = [value for value in values if value]
    return max(valid) if valid else BUILD_DATE


def write_sitemap(markets, guides, by_market):
    urls = []
    page_files = SITEMAP_ROOT_FILES + [data["landing_page"] for data in markets.values()]
    landing_to_market = {data["landing_page"]: key for key, data in markets.items()}
    for filename in page_files:
        path = DIST / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing sitemap page: {path}")
        canonical = read_canonical(path)
        if not canonical:
            continue
        lastmod = source_lastmod(filename)
        market_key = landing_to_market.get(filename)
        if market_key and by_market.get(market_key):
            lastmod = max_date(lastmod, max(item["updated"] for item in by_market[market_key]))
        urls.append((canonical, lastmod))
    for guide in guides:
        urls.append((SITE_URL + guide["url"], guide["updated"]))
    for market, items in by_market.items():
        if items:
            urls.append((SITE_URL + f"/guides/{market}/", max(item["updated"] for item in items)))
    seen = set()
    clean = []
    for url, lastmod in urls:
        if url not in seen:
            seen.add(url)
            clean.append((url, lastmod))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in clean:
        lines.extend(["  <url>", f"    <loc>{html.escape(url)}</loc>", f"    <lastmod>{html.escape(lastmod)}</lastmod>", "  </url>"])
    lines.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(markets, redirects, guides):
    problems = []
    for market in markets.values():
        formal = DIST / market["landing_page"]
        alias = DIST / market["landing_page"].removesuffix(".html") / "index.html"
        if not formal.exists():
            problems.append(f"Missing formal route page: {formal}")
        if not alias.exists():
            problems.append(f"Missing active alias redirect: {alias}")
    for item in redirects:
        formal = DIST / item["source"]
        alias = DIST / item["source"].removesuffix(".html") / "index.html"
        if not formal.exists() or "noindex,follow" not in formal.read_text(encoding="utf-8"):
            problems.append(f"Missing retired root redirect: {formal}")
        if not alias.exists() or "noindex,follow" not in alias.read_text(encoding="utf-8"):
            problems.append(f"Missing retired alias redirect: {alias}")
    for guide in guides:
        if not (DIST / guide["url"].lstrip("/")).exists():
            problems.append(f'Missing guide: {guide["url"]}')
    for required in ["sitemap.xml", "robots.txt", "index.html", "CNAME"]:
        if not (DIST / required).exists():
            problems.append(f"Missing output: {required}")
    sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    for item in redirects:
        if item["source"] in sitemap:
            problems.append(f'Retired URL leaked into sitemap: {item["source"]}')
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)


def main():
    markets = load_markets()
    redirects = load_redirects()
    copy_source()
    guides = load_guides(markets)
    by_market = generate_guides(markets, guides)
    inject_organization()
    inject_route_enhancements(markets, by_market)
    write_redirect_pages(markets, redirects)
    write_robots()
    write_sitemap(markets, guides, by_market)
    validate(markets, redirects, guides)
    print(f"Built {len(markets)} focused landing pages, {len(redirects)} EU-country redirects and {len(guides)} published guides into {DIST}")


if __name__ == "__main__":
    main()
