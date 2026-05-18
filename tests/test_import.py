"""Import smoke tests for the nkcalc package."""

import nkcalc


def test_import_has_version() -> None:
    """The package imports and exposes a version string."""
    assert isinstance(nkcalc.__version__, str)
    assert nkcalc.__version__
