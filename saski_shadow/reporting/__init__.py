"""HTML rendering for shadow pilot reports.

Zero runtime dependencies: rendering uses only the Python standard library. The
HTML produced is fully self-contained (inline CSS, no external assets) so it can
be emailed or opened offline.
"""

from .html_report import generate_html_report

__all__ = ["generate_html_report"]
