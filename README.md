# nkcalc

`nkcalc` is a Python package for staged development of optical `n(λ), k(λ)` tools for
Ge, SiGe, and Si.

The package is currently in Phase 0: repository bootstrap. Physics models are intentionally
not implemented yet.

## Development

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run checks:

```bash
pytest -q
ruff check src tests
```
