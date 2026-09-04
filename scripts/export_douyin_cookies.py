"""Export only Douyin cookies from a local browser into a Netscape jar.

Cookie values are never printed. The resulting file is sensitive and must stay
outside the Git repository; ``D:\\autodub_secrets`` is the recommended location.
"""

from __future__ import annotations

import argparse
import copy
from http.cookiejar import Cookie, MozillaCookieJar
from pathlib import Path
from typing import Iterable

from yt_dlp.cookies import extract_cookies_from_browser


ALLOWED_COOKIE_DOMAINS = ("douyin.com", "iesdouyin.com")
RECOMMENDED_COOKIE_NAMES = {"ttwid", "odin_tt", "passport_csrf_token"}


def is_douyin_cookie(cookie: Cookie) -> bool:
    domain = str(cookie.domain or "").lower().lstrip(".")
    return any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_COOKIE_DOMAINS)


def filtered_cookie_jar(cookies: Iterable[Cookie], output: Path) -> MozillaCookieJar:
    jar = MozillaCookieJar(str(output))
    for cookie in cookies:
        if is_douyin_cookie(cookie):
            jar.set_cookie(copy.copy(cookie))
    return jar


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", default="chrome", choices=("chrome", "edge", "firefox"))
    parser.add_argument("--profile", default=None)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = extract_cookies_from_browser(args.browser, profile=args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    jar = filtered_cookie_jar(source, args.output)
    jar.save(ignore_discard=True, ignore_expires=True)

    names = sorted({cookie.name for cookie in jar})
    missing = sorted(RECOMMENDED_COOKIE_NAMES.difference(names))
    print(f"Exported {len(list(jar))} Douyin cookies to {args.output}")
    print("Cookie names: " + ", ".join(names))
    if missing:
        print("Warning - recommended cookies not found: " + ", ".join(missing))
    return 0 if names else 2


if __name__ == "__main__":
    raise SystemExit(main())
