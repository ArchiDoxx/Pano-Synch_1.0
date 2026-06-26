from backend.version import __version__


def test_version_is_set():
    assert __version__ == "1.5"
