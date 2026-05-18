"""Generate a Ge Frey-style Sellmeier table from YAML parameters."""

import numpy as np

from nkcalc.materials.ge import ge_frey_sellmeier


def main() -> None:
    """Print a small transparent-side Ge Sellmeier table."""
    lambda_um = np.linspace(1.9, 5.5, 5)
    model = ge_frey_sellmeier(temperature_K=295.0)
    print(model.table(lambda_um))


if __name__ == "__main__":
    main()
