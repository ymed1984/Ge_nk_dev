"""Compare Ge facade backends with a common table interface."""

import numpy as np

from nkcalc.materials.ge import GeOpticalModel


def main() -> None:
    """Print a small Ge Frey Sellmeier facade table."""
    lambda_um = np.linspace(1.9, 5.5, 5)
    ge = GeOpticalModel.frey_sellmeier(temperature_K=295.0)
    print(ge.table(lambda_um))


if __name__ == "__main__":
    main()
