"""GitHub Pages subpath support: the base path is derived from SITE_URL, applied to
every root-absolute href/src/action in generated HTML, and never double-applied to
canonical URLs or the sitemap (which already embed it via SITE_URL itself).

build.py fixes SITE_URL (and the derived BASE_PATH) as module-level constants at
import time, so these tests drive the real CLI entry points as subprocesses -- the
same way `make build` / `make check` do -- rather than importing and reloading the
module under different environments.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DIST = ROOT / "dist"
BUILD_SCRIPT = ROOT / "scripts" / "build.py"
CHECK_SCRIPT = ROOT / "scripts" / "check_site.py"

ROOT_SITE_URL = "https://deployindex.com"
SUBPATH_SITE_URL = "https://embark-delve.github.io/deploy-index"
BASE_PATH = "/deploy-index"


def run(script: Path, site_url: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["SITE_URL"] = site_url
    env.pop("CI", None)
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class PagesSubpathTests(unittest.TestCase):
    """Builds into the real dist/ (there is no CLI flag for an alternate output
    directory), backs up whatever was already there, and always restores it --
    the default build the rest of the toolchain relies on must stay a root build.
    """

    _backup: Path | None = None

    @classmethod
    def setUpClass(cls) -> None:
        if DIST.exists():
            cls._backup = ROOT / "dist.test-backup"
            if cls._backup.exists():
                shutil.rmtree(cls._backup)
            shutil.move(str(DIST), str(cls._backup))

    @classmethod
    def tearDownClass(cls) -> None:
        if DIST.exists():
            shutil.rmtree(DIST)
        if cls._backup is not None:
            shutil.move(str(cls._backup), str(DIST))

    def build(self, site_url: str) -> None:
        result = run(BUILD_SCRIPT, site_url)
        self.assertEqual(
            result.returncode, 0,
            f"build.py failed for SITE_URL={site_url!r}:\n{result.stdout}\n{result.stderr}",
        )

    def test_root_site_url_leaves_root_absolute_urls_unprefixed(self) -> None:
        self.build(ROOT_SITE_URL)
        index_html = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/assets/styles.css"', index_html)
        self.assertIn('<link rel="canonical" href="https://deployindex.com/" />', index_html)
        # No base path -> the data-base-path attribute must not appear at all, so a
        # root build's <html> tag stays byte-identical to today's output.
        self.assertNotIn("data-base-path", index_html)

    def test_subpath_site_url_prefixes_generated_html(self) -> None:
        self.build(SUBPATH_SITE_URL)
        index_html = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/deploy-index/assets/styles.css"', index_html)
        self.assertIn('src="/deploy-index/assets/theme.js"', index_html)
        self.assertIn(f'data-base-path="{BASE_PATH}"', index_html)
        # A provider detail page templated through the same choke point picks it up too.
        provider_pages = sorted((DIST / "providers").glob("*/index.html"))
        self.assertTrue(provider_pages)
        provider_html = provider_pages[0].read_text(encoding="utf-8")
        self.assertIn('href="/deploy-index/"', provider_html)  # brand link in header

    def test_subpath_build_does_not_double_prefix_canonical_or_sitemap(self) -> None:
        self.build(SUBPATH_SITE_URL)
        index_html = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            f'<link rel="canonical" href="{SUBPATH_SITE_URL}/" />', index_html,
        )
        self.assertNotIn("/deploy-index/deploy-index/", index_html)

        sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"<loc>{SUBPATH_SITE_URL}/</loc>", sitemap)
        self.assertNotIn("/deploy-index/deploy-index/", sitemap)

        robots = (DIST / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(robots.splitlines()[-1], f"Sitemap: {SUBPATH_SITE_URL}/sitemap.xml")
        self.assertNotIn("/deploy-index/deploy-index/", robots)

    def test_external_urls_are_never_rewritten(self) -> None:
        self.build(SUBPATH_SITE_URL)
        index_html = (DIST / "index.html").read_text(encoding="utf-8")
        # The GitHub link in the header nav is an external, absolute URL.
        self.assertIn('href="https://github.com/"', index_html)
        self.assertNotIn("/deploy-indexhttps://", index_html)
        self.assertNotIn('href="/deploy-index//', index_html)  # would indicate a "//" protocol-relative URL got mangled

    def test_no_unprefixed_root_absolute_url_survives_a_subpath_build(self) -> None:
        self.build(SUBPATH_SITE_URL)
        import re

        attr_re = re.compile(r'\b(?:href|src|action)="(/[^"]*)"')
        offenders: list[str] = []
        for html_file in DIST.rglob("*.html"):
            text = html_file.read_text(encoding="utf-8")
            for match in attr_re.finditer(text):
                value = match.group(1)
                if value.startswith("//"):
                    continue  # protocol-relative, not root-absolute
                if not (value == BASE_PATH or value.startswith(BASE_PATH + "/")):
                    offenders.append(f"{html_file.relative_to(DIST)}: {match.group(0)}")
        self.assertEqual(offenders, [], f"unprefixed root-absolute URLs found:\n" + "\n".join(offenders))

    def test_check_site_passes_against_a_subpath_build(self) -> None:
        self.build(SUBPATH_SITE_URL)
        result = run(CHECK_SCRIPT, SUBPATH_SITE_URL)
        self.assertEqual(
            result.returncode, 0,
            f"check_site.py failed against a subpath build:\n{result.stdout}\n{result.stderr}",
        )

    def test_check_site_flags_a_root_absolute_link_missing_the_base_path(self) -> None:
        self.build(SUBPATH_SITE_URL)
        # Simulate a bug: a hand-authored root-absolute link that forgot the prefix.
        bad_file = DIST / "index.html"
        text = bad_file.read_text(encoding="utf-8")
        self.assertIn('href="/deploy-index/assets/styles.css"', text)
        tampered = text.replace(
            'href="/deploy-index/assets/styles.css"', 'href="/assets/styles.css"', 1,
        )
        bad_file.write_text(tampered, encoding="utf-8")
        result = run(CHECK_SCRIPT, SUBPATH_SITE_URL)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
