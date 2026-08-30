#!/usr/bin/env python3
"""Validate the generated static site, internal links, and catalog API files."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from catalog import ROOT, load_catalog
from recommendations import validate_recommendation_catalog

DIST = ROOT / "dist"
TEMPLATE_TOKEN = re.compile(r"\{\{[^{}]+\}\}|__\w+__")

# Mirrors build.py's derivation: the base path a GitHub Pages (or other subpath)
# deployment was built with, taken from the same SITE_URL environment variable so
# there is no second knob to keep in sync.
SITE_URL = (os.environ.get("SITE_URL") or "http://localhost:8000").rstrip("/")
BASE_PATH = urlparse(SITE_URL).path.rstrip("/")


class MissingBasePathError(ValueError):
    """A root-absolute link doesn't carry the expected BASE_PATH prefix."""


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.ids: list[str] = []
        self.has_main = False
        self.h1_count = 0
        self.title_text = ""
        self._in_title = False
        self.meta_description = False
        self.html_lang = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html" and values.get("lang"):
            self.html_lang = True
        if tag == "title":
            self._in_title = True
        if tag == "main":
            self.has_main = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "meta" and values.get("name") == "description" and values.get("content"):
            self.meta_description = True
        if values.get("id"):
            self.ids.append(values["id"] or "")
        for attribute in ("href", "src"):
            if values.get(attribute):
                self.links.append(values[attribute] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_text += data


def target_path(dist: Path, current: Path, href: str) -> tuple[Path | None, str | None]:
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc or href.startswith(("mailto:", "tel:", "data:")):
        return None, None
    fragment = unquote(parsed.fragment) or None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return current, fragment
    if raw_path.startswith("/"):
        if BASE_PATH:
            if raw_path == BASE_PATH or raw_path.startswith(BASE_PATH + "/"):
                raw_path = raw_path[len(BASE_PATH):] or "/"
            else:
                raise MissingBasePathError(href)
        target = dist / raw_path.lstrip("/")
    else:
        target = current.parent / raw_path
    if raw_path.endswith("/") or target.is_dir():
        target = target / "index.html"
    elif not target.suffix:
        target = target / "index.html"
    return target.resolve(), fragment


def parse_html(path: Path) -> tuple[DocumentParser, str]:
    text = path.read_text(encoding="utf-8")
    parser = DocumentParser()
    parser.feed(text)
    return parser, text


def check(dist: Path) -> list[str]:
    errors: list[str] = []
    if not dist.exists():
        return [f"Build directory does not exist: {dist}"]
    html_files = sorted(dist.rglob("*.html"))
    if not html_files:
        return ["No HTML files generated"]

    parsed_docs: dict[Path, DocumentParser] = {}
    for path in html_files:
        parser, text = parse_html(path)
        resolved = path.resolve()
        parsed_docs[resolved] = parser
        rel = path.relative_to(dist)
        if TEMPLATE_TOKEN.search(text):
            errors.append(f"{rel}: unresolved template token")
        if not parser.html_lang:
            errors.append(f"{rel}: missing html lang")
        if not parser.title_text.strip():
            errors.append(f"{rel}: missing title")
        if not parser.meta_description:
            errors.append(f"{rel}: missing meta description")
        if not parser.has_main:
            errors.append(f"{rel}: missing main landmark")
        if parser.h1_count != 1:
            errors.append(f"{rel}: expected exactly one h1, found {parser.h1_count}")
        if len(parser.ids) != len(set(parser.ids)):
            errors.append(f"{rel}: duplicate element IDs")

    for current, parser in parsed_docs.items():
        for href in parser.links:
            try:
                target, fragment = target_path(dist.resolve(), current, href)
            except MissingBasePathError:
                errors.append(
                    f"{current.relative_to(dist.resolve())}: root-absolute link is missing "
                    f"the expected base path {BASE_PATH!r}: {href}"
                )
                continue
            if target is None:
                continue
            try:
                target.relative_to(dist.resolve())
            except ValueError:
                errors.append(f"{current.relative_to(dist.resolve())}: local link escapes dist: {href}")
                continue
            if not target.exists():
                errors.append(f"{current.relative_to(dist.resolve())}: broken local link {href}")
                continue
            if fragment and target.suffix == ".html":
                target_parser = parsed_docs.get(target)
                if target_parser is None:
                    target_parser, _ = parse_html(target)
                    parsed_docs[target] = target_parser
                if fragment not in target_parser.ids:
                    errors.append(f"{current.relative_to(dist.resolve())}: missing fragment target {href}")

    # Python accepts the non-standard tokens Infinity / -Infinity / NaN; browsers
    # and every other JSON parser do not. Reject them so a payload that no
    # consumer can read cannot pass this check.
    def _reject_non_standard(token: str) -> None:
        raise ValueError(f"non-standard JSON token {token}")

    for api_file in ("catalog/providers.json", "catalog/schema.json", "catalog/stats.json", "catalog/recommendations.json", "catalog/pricing.json"):
        try:
            json.loads((dist / api_file).read_text(encoding="utf-8"), parse_constant=_reject_non_standard)
        except (OSError, ValueError) as exc:
            errors.append(f"{api_file}: invalid or missing JSON: {exc}")

    catalog = load_catalog()
    try:
        recommendation_payload = json.loads((dist / "catalog" / "recommendations.json").read_text(encoding="utf-8"))
        errors.extend(f"catalog/recommendations.json: {error}" for error in validate_recommendation_catalog(recommendation_payload, catalog))
    except (OSError, json.JSONDecodeError):
        pass
    for item in catalog["providers"]:
        page = dist / "providers" / item["slug"] / "index.html"
        if not page.exists():
            errors.append(f"Missing provider detail page: {item['slug']}")
    for tool_page in ("recommend", "method", "compare", "pricing"):
        if not (dist / tool_page / "index.html").exists():
            errors.append(f"Missing tool page: /{tool_page}/")
    expected_sitemap_entries = len(catalog["providers"]) + 6
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    if sitemap.count("<url>") != expected_sitemap_entries:
        errors.append(
            f"sitemap.xml: expected {expected_sitemap_entries} URL entries, found {sitemap.count('<url>')}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=DIST)
    args = parser.parse_args()
    errors = check(args.dist)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    html_count = len(list(args.dist.rglob("*.html")))
    print(f"Static site valid: {html_count} HTML files, internal links and JSON APIs checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
