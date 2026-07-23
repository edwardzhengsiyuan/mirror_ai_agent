"""Print-oriented MingShu (命书) fact and editorial planning helpers."""

from .blueprint import STANDARD_EDITION, build_standard_blueprint
from .composer import BOOK_SCHEMA_VERSION, compose_book


def build_book_facts(*args, **kwargs):
    """Import the BaZi engine lazily so PDF-only runtimes stay lightweight."""
    from .facts import build_book_facts as _build_book_facts

    return _build_book_facts(*args, **kwargs)

__all__ = [
    "BOOK_SCHEMA_VERSION",
    "STANDARD_EDITION",
    "build_book_facts",
    "build_standard_blueprint",
    "compose_book",
]
