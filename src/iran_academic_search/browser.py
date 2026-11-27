"""Camoufox-backed public page fetcher; no CAPTCHA or login bypass."""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from camoufox.sync_api import Camoufox

from .sites import SITES, Site

_lock = threading.Lock()
_manager = None
_browser = None
_context = None
_last_navigation = 0.0
_magiran_authenticated = False
_inspection_page = None


def _load_local_env() -> None:
    """Load the small, gitignored local config without a dotenv dependency."""
    root_env = Path(__file__).resolve().parents[2] / ".env"
    env_file = Path(os.getenv("IRAN_MCP_ENV_FILE", str(root_env)))
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value.startswith(("'", '"')) and value.endswith(value[0]):
            value = value[1:-1]
        if key in {"MAGIRAN_USERNAME", "MAGIRAN_PASSWORD", "IRAN_MCP_HEADLESS"}:
            if not os.getenv(key):
                os.environ[key] = value


_load_local_env()
_HEADLESS = os.getenv("IRAN_MCP_HEADLESS", "true").strip().casefold() not in {
    "0", "false", "no", "off"
}


def _env_float(name: str, default: float, lower: float, upper: float) -> float:
    try:
        return max(lower, min(upper, float(os.getenv(name, str(default)))))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, lower: int, upper: int) -> int:
    try:
        return max(lower, min(upper, int(os.getenv(name, str(default)))))
    except (TypeError, ValueError):
        return default


def _magiran_credentials() -> tuple[str, str]:
    """Read credentials from process environment or the ignored local .env file."""
    username = os.getenv("MAGIRAN_USERNAME", "")
    password = os.getenv("MAGIRAN_PASSWORD", "")
    if not username or not password:
        raise RuntimeError(
            "اعتبارنامهٔ مگیران تنظیم نشده است؛ MAGIRAN_USERNAME و MAGIRAN_PASSWORD را "
            "در متغیرهای محیطی یا فایل .env محلی قرار دهید."
        )
    return username, password


_NAV_DELAY = _env_float("IRAN_MCP_NAV_DELAY", 1.2, 0.5, 60.0)
_MAX_TEXT = _env_int("IRAN_MCP_MAX_TEXT", 30_000, 5_000, 100_000)


@dataclass
class PageData:
    url: str
    title: str
    text: str
    links: list[dict[str, str]]


def _ensure_browser():
    global _manager, _browser, _context
    if _context is not None:
        # Pages are intentionally closed after each fetch. An empty page list
        # does not mean the persistent browser context itself has closed.
        return _context
    _manager = Camoufox(headless=_HEADLESS, humanize=False)
    try:
        _context = _manager.__enter__()
    except Exception:
        _manager = None
        raise
    return _context


def _allowed_url(url: str, site: Site) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in site.domains)


def _clean_text(text: str) -> str:
    text = text.replace("\u200f", "").replace("\u200e", "")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch(url: str, site: Site, timeout_ms: int = 25_000) -> PageData:
    """Fetch a single public page, enforcing site host allowlist and polite pacing."""
    global _last_navigation, _inspection_page
    if not _allowed_url(url, site):
        raise ValueError(f"URL خارج از دامنهٔ مجاز {site.name} است.")
    import time

    with _lock:
        remaining = _NAV_DELAY - (time.monotonic() - _last_navigation)
        if remaining > 0:
            time.sleep(remaining)
        context = _ensure_browser()
        page = context.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=min(timeout_ms, 30_000))
            if not _allowed_url(page.url, site):
                raise RuntimeError("سایت به نشانی خارج از دامنهٔ مجاز هدایت کرد.")
            try:
                page.locator("body").wait_for(timeout=5_000)
            except Exception:
                pass
            # Allow lightweight client rendering without waiting indefinitely for analytics.
            page.wait_for_timeout(500)
            title = _clean_text(page.title())
            text = _clean_text(page.locator("body").inner_text(timeout=5_000))[:_MAX_TEXT]
            if site.key == "sid" and "transferring to the website" in text.casefold():
                # SID can first show a short, script-driven transfer page before
                # navigating to the actual search results. Give that normal
                # page transition time to finish; do not interact with or solve
                # any CAPTCHA or human-verification challenge.
                try:
                    page.wait_for_function(
                        "document.body && document.body.innerText.trim() && "
                        "!document.body.innerText.toLowerCase().includes('transferring to the website')",
                        timeout=12_000,
                    )
                except Exception:
                    pass
                page.wait_for_timeout(500)
                title = _clean_text(page.title())
                text = _clean_text(page.locator("body").inner_text(timeout=5_000))[:_MAX_TEXT]
                if "transferring to the website" in text.casefold():
                    raise RuntimeError(
                        "SID پس از انتظار هنوز صفحهٔ واسط انتقال را نشان می‌دهد؛ "
                        "نتایج در دسترس نیستند و بررسی ضدربات دور زده نمی‌شود."
                    )
            links: list[dict[str, str]] = []
            # Header/footer navigation can contain many links before results. A
            # larger bounded sample improves discovery without dumping the page.
            for anchor in page.locator("a[href]").all()[:300]:
                try:
                    href = anchor.get_attribute("href") or ""
                    label = _clean_text(anchor.inner_text(timeout=700))
                    if site.key == "sid" and label in {"مقاله نشریه", "دانلود", "نسخه انگلیسی"}:
                        # SID renders several action links next to each record.
                        # Their own captions are generic, so recover the record
                        # title from the nearest result card to avoid returning
                        # misleading titles such as "Download" as papers.
                        record_title = anchor.evaluate(
                            """el => {
                                for (let node = el; node && node !== document.body; node = node.parentElement) {
                                    const text = node.innerText || '';
                                    const match = text.match(/عنوان\\s*[:：]\\s*([^\\r\\n]+)/);
                                    if (match && match[1].trim().length > 5) return match[1].trim();
                                }
                                return '';
                            }"""
                        )
                        if record_title:
                            label = _clean_text(record_title)
                    absolute = anchor.evaluate("el => el.href")
                    if label and _allowed_url(absolute, site):
                        links.append({"title": label[:240], "url": absolute})
                except Exception:
                    continue
            status = response.status if response is not None else None
            if status and status >= 400:
                raise RuntimeError(f"سایت پاسخ HTTP {status} داد.")
            if any(s in text.lower() for s in ("captcha", "کد امنیتی", "اعتبارسنجی انسانی")):
                raise RuntimeError("سایت CAPTCHA یا بررسی انسانی نشان داد؛ این MCP آن را دور نمی‌زند.")
            _last_navigation = time.monotonic()
            return PageData(page.url, title, text, links)
        finally:
            if _HEADLESS:
                page.close()
            else:
                # Keep inspected pages open in visible mode for user review.
                _inspection_page = page


def login_magiran() -> dict[str, str]:
    """Sign in through Magiran's normal public login form; never bypass challenges."""
    global _magiran_authenticated, _inspection_page
    username, password = _magiran_credentials()
    with _lock:
        if _magiran_authenticated:
            return {"source": "magiran", "status": "ok", "message": "نشست مگیران فعال است."}
        context = _ensure_browser()
        page = context.new_page()
        try:
            response = page.goto(
                "https://www.magiran.com/Account/Login",
                wait_until="domcontentloaded",
                timeout=25_000,
            )
            if response is not None and response.status >= 400:
                raise RuntimeError(f"صفحهٔ ورود مگیران پاسخ HTTP {response.status} داد.")
            page.locator("#Email").fill(username, timeout=8_000)
            page.locator("#Password").fill(password, timeout=8_000)
            try:
                with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
                    page.locator("#submitButton").click(timeout=8_000)
            except Exception:
                # Some site revisions submit without a full navigation. Inspect
                # the resulting page below before deciding whether auth worked.
                pass
            try:
                page.wait_for_function(
                    "document.body && (document.body.innerText.includes('خوش آمدید') "
                    "|| document.body.innerText.includes('خروج'))",
                    timeout=8_000,
                )
            except Exception:
                pass
            body = _clean_text(page.locator("body").inner_text(timeout=5_000))
            if any(marker in body.casefold() for marker in ("captcha", "کد امنیتی", "اعتبارسنجی انسانی")):
                raise RuntimeError("مگیران بررسی انسانی نشان داد؛ این ابزار آن را دور نمی‌زند.")
            still_on_login = "/account/login" in urlparse(page.url).path.casefold()
            has_password_field = page.locator("#Password").count() > 0
            login_links = page.locator("a[href]").evaluate_all(
                "anchors => anchors.map(a => ({text: a.innerText.trim(), href: a.href}))"
            )
            authenticated_marker = (
                username.casefold() in body.casefold()
                or "خوش آمدید" in body
                or any(
                    "خروج" in link["text"]
                    or "logout" in link["href"].casefold()
                    for link in login_links
                )
            )
            if still_on_login or has_password_field or not authenticated_marker:
                details = page.locator("#Login").locator(
                    ".validation-summary-errors, .field-validation-error, "
                    ".alert-danger, [role='alert'], [data-valmsg-summary='true']"
                ).all_inner_texts()
                message = _clean_text(" ".join(details))
                raise RuntimeError(
                    message
                    or "مگیران ورود را تأیید نکرد؛ ایمیل و گذرواژه را بررسی کنید و مطمئن شوید "
                    "حساب به صفحهٔ اصلی هدایت شده است."
                )
            _magiran_authenticated = True
            return {
                "source": "magiran",
                "status": "ok",
                "url": page.url,
                "message": "ورود به مگیران موفق بود؛ سطح دسترسی تابع اشتراک حساب است.",
            }
        finally:
            if _HEADLESS:
                page.close()
            else:
                # Leave the final login state on screen so the user can inspect it.
                _inspection_page = page


def close_browser() -> None:
    """Close the persistent Camoufox context cleanly on server shutdown."""
    global _manager, _context
    manager = _manager
    _manager = None
    _browser = None
    _context = None
    if manager is not None:
        manager.__exit__(None, None, None)
