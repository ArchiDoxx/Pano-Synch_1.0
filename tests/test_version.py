from backend.app import inject_version, __version__
from fastapi import Request


def test_version_is_set():
    assert __version__ == "1.5"


def test_inject_version_context_processor():
    request = Request(scope={"type": "http", "method": "GET", "path": "/"})
    assert inject_version(request) == {"version": __version__}
