"""Site profiles and conservative extraction rules for public search pages."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    home: str
    search_urls: tuple[str, ...]
    domains: tuple[str, ...]


SITES: dict[str, Site] = {
    "ensani": Site(
        "ensani",
        "پرتال جامع علوم انسانی (Ensani)",
        "https://www.ensani.ir/fa",
        (
            "https://www.ensani.ir/fa/article/search/advance-search?AdvanceSearch%5BallWordMatch%5D={query}",
        ),
        ("ensani.ir",),
    ),
    "noormags": Site(
        "noormags",
        "نورمگز",
        "https://www.noormags.ir/view/fa/default",
        (
            "https://www.noormags.ir/view/fa/search?query={query}",
        ),
        ("noormags.ir",),
    ),
    "sid": Site(
        "sid",
        "پایگاه اطلاعات علمی جهاد دانشگاهی (SID)",
        "https://sid.ir/",
        ("https://sid.ir/search/paper/{query}",),
        ("sid.ir",),
    ),
    "magiran": Site(
        "magiran",
        "مگیران",
        "https://www.magiran.com/",
        ("https://www.magiran.com/searchinpapers?aw={query}&cols=1%2C2%2C3%2C4",),
        ("magiran.com",),
    ),
}


def format_search_url(template: str, query: str) -> str:
    return template.format(query=quote_plus(query))
