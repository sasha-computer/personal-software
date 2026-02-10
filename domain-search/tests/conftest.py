import io

from rich.console import Console


def _capture_console() -> tuple[Console, io.StringIO]:
    """Create a Console that writes to a StringIO for test capturing."""
    buf = io.StringIO()
    return Console(file=buf, force_terminal=True, width=120), buf
