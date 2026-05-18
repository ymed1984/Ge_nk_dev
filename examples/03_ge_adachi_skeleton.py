"""Evaluate the placeholder Ge Adachi-style critical-point scaffold."""

import numpy as np

from nkcalc.models.adachi_ge import AdachiGeModel


def main() -> None:
    """Print a small table from the placeholder critical-point scaffold."""
    model = AdachiGeModel.from_yaml("data/params/ge_adachi_initial.yml")
    lambda_um = np.linspace(0.8, 3.0, 5)
    print(model.table(lambda_um))
    print("implemented_terms:", model.implemented_terms)
    print("source_notes:", model.source_notes)


if __name__ == "__main__":
    main()
