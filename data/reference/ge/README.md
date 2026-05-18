# Ge reference CSV data

Place user-provided Ge reference data in this directory when using `TabulatedModel`.

Reference CSV files are not bundled from the local PDFs. If you create a CSV from a paper,
database, or measurement, make sure you have the right to use that data locally and keep the
source traceable in your own notes or sidecar metadata.

Supported wavelength column names:

- `lambda_um`
- `wavelength_um`
- `lambda_nm`
- `wavelength_nm`

Supported data formats:

```csv
lambda_um,n,k
1.0,3.0,0.01
2.0,3.2,0.04
```

```csv
lambda_um,eps1,eps2
1.0,9.0,0.06
2.0,10.0,0.10
```

The tiny examples above are synthetic format examples, not literature data.
