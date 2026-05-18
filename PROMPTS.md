# PROMPTS.md — `nkcalc` Codex 実装用プロンプト集

このファイルは、Codexへ順番に投入するためのプロンプト集である。基本的には P0 から順に実行する。各プロンプトは独立性を高めているが、前段の成果物を前提にする。

---

## 使い方

1. リポジトリの root に `AGENTS.md`, `EXECPLAN.md`, `PROMPTS.md` を置く。
2. CodexにP0から順に依頼する。
3. 各タスク完了後、`pytest -q` と `ruff check src tests` の結果を確認する。
4. 失敗があれば該当プロンプトの「修正用プロンプト」を使う。

---

## ローカルPDF文献の扱い

このリポジトリには、背景確認用の論文PDFを `pdf/` 配下に置く。実装プロンプトでは、必要に応じてこれらを参照して、モデル式、validity range、温度範囲、物理的な注意点、validation 観点を確認する。

```text
pdf/
  Temperature-dependent refractive index of silicon and germanium.pdf
  PhysRevB.27.985.pdf
  Temperaturedependent dielectricfunctionanddirectBandgapofGe.pdf
  PhysRevB.38.12966.pdf
  Si Temp Prameters.pdf
```

参照ルール:

- PDFは背景・式・定義・適用範囲の確認に使う。
- PDF中の大きな表、長い数表、図の数値トレース結果を、そのままコード・テスト・CSVへ転載しない。
- 文献係数を実装に使う場合は、リポジトリ内に明示的な許可済み YAML/CSV がある場合、またはユーザーがその場で値の使用を指示した場合に限る。
- 係数が未確認なら `placeholder`, `synthetic`, `initial`, `to_be_fitted` のいずれかを名前・コメント・メタデータに入れる。
- 実装完了報告では、どのPDFを参照したか、どの値が実文献値ではなく仮値かを明記する。

文献の主な使い分け:

- Frey/Leviton/Madison 系: `Temperature-dependent refractive index of silicon and germanium.pdf` を Ge/Si の透明側 Sellmeier と温度範囲の確認に使う。
- Aspnes & Studna 系: `PhysRevB.27.985.pdf` を Ge/Si の誘電関数、`n,k,alpha` validation の背景確認に使う。
- Emminger 系: `Temperaturedependent dielectricfunctionanddirectBandgapofGe.pdf` を Ge の温度依存誘電関数と直接バンドギャップ近傍の validation 観点に使う。
- Adachi 系: `PhysRevB.38.12966.pdf` を critical-point 誘電関数モデルの構造確認に使う。
- Green/Si 温度係数系: `Si Temp Prameters.pdf` を Si 拡張時の温度依存・validation 方針確認に使う。

---

## ローカルLumerical標準データの扱い

`bgdata/` 配下には、Lumerical 標準モデル由来の背景比較データを置く。

```text
bgdata/
  Ge (Germanium) - CRC.csv
```

確認済みの構造:

- format: CSV
- columns: `wavelength(m)`, `Re(n_xx)`, `Im(n_xx)`
- 想定: Ge, 歪みなし, CRC/Lumerical 標準モデル系の `n,k` benchmark

扱いのルール:

- このファイルは、Ge facade、CLI、validation、plot、model comparison の背景 benchmark として必要に応じて参照する。
- 本体モデルの係数や物理式としては使わない。まず `TabulatedModel` で読み込める user/local reference data として扱う。
- 実装に loader を追加する場合は、列名と単位変換を明示し、`wavelength(m) * 1e6 -> lambda_um`, `Re(n_xx) -> n`, `Im(n_xx) -> k` として扱う。
- metadata には `source="Lumerical standard Ge CRC"`, `strain_state="unstrained"` などを残す。
- テストでは、この実ファイルに依存しすぎない。基本は synthetic data を使い、実ファイルを使う場合は存在チェック付きの optional/smoke 的検証に留める。
- Lumerical/CRC データ rows を再配布用テンプレートや example CSV に複製しない。

---

## P0 — Repository bootstrap

```text
You are working in the nkcalc repository. Read AGENTS.md and EXECPLAN.md first.

Implement Phase 0: Repository bootstrap.

Create a Python package skeleton for nkcalc with:
- pyproject.toml
- README.md
- src/nkcalc/__init__.py
- src/nkcalc/cli.py with a minimal Typer app
- tests/test_import.py

Use Python >=3.11. Dependencies should include numpy, scipy, pandas, matplotlib, pyyaml, typer. Dev dependencies should include pytest and ruff.

Acceptance criteria:
- python -m pip install -e .[dev] works
- pytest -q passes
- ruff check src tests passes

Do not implement physics models yet. Keep this task small.

At the end, report changed files and test results.
```

---

## P1 — Core numerics: units, epsilon, n/k, alpha

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 1: Core numerics.

Add:
- src/nkcalc/constants.py
- src/nkcalc/spectrum.py
- src/nkcalc/core/__init__.py
- src/nkcalc/core/nk.py
- tests/test_units.py
- tests/test_nk_conversion.py
- tests/test_alpha_conversion.py

Required functions:
- wavelength_um_to_energy_ev(lambda_um)
- energy_ev_to_wavelength_um(energy_ev)
- energy_ev_to_omega_rad_s(energy_ev)
- epsilon_to_nk(eps_complex)
- nk_to_epsilon(n, k)
- k_to_alpha_m_inv(k, lambda_um)
- k_to_alpha_cm_inv(k, lambda_um)
- alpha_cm_inv_to_k(alpha_cm_inv, lambda_um)

Rules:
- Use lambda_um for wavelength in microns.
- Use HC_EV_UM = 1.239841984.
- epsilon_to_nk must choose the passive branch with k >= 0 for passive media.
- All functions must accept scalar-like or numpy array input and return numpy arrays, except where scalar passthrough is naturally simple.
- Include docstrings specifying units.

Acceptance criteria:
- lambda -> energy -> lambda round trip passes.
- n,k -> eps -> n,k round trip passes for representative absorbing and transparent cases.
- alpha = 4*pi*k/lambda conversion passes.
- pytest -q and ruff check pass.

At the end, report changed files and test results.
```

---

## P2 — CSV and Lumerical export

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 2: IO and Lumerical export.

Add:
- src/nkcalc/io/__init__.py
- src/nkcalc/io/csv_io.py
- src/nkcalc/io/lumerical.py
- tests/test_lumerical_export.py

Implement:
- ensure_required_columns(df, columns)
- export_table_csv(df, path)
- export_lumerical_nk_txt(df, path, wavelength_unit="um", header=False, allow_negative_k=False)

Lumerical export must write 3 columns:
- wavelength, n, k

Rules:
- Internal DataFrame column is lambda_um.
- wavelength_unit may be "um" or "nm".
- Default is header=False.
- Reject NaN/inf.
- Reject k < 0 unless allow_negative_k=True.
- Do not silently rename columns.

Acceptance criteria:
- Unit tests verify formatting, header option, wavelength unit conversion, and validation errors.
- pytest -q and ruff check pass.

At the end, report changed files and test results.
```

---

## P3 — TabulatedModel

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 3: Tabulated model.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.

Add:
- src/nkcalc/models/__init__.py
- src/nkcalc/models/base.py
- src/nkcalc/models/tabulated.py
- src/nkcalc/core/validation.py if needed for range checks
- tests/test_tabulated_model.py
- data/reference/ge/README.md

Implement BaseOpticalModel with:
- epsilon(lambda_um)
- nk(lambda_um)
- table(lambda_um)

Implement TabulatedModel with:
- from_nk_csv(path, wavelength_unit="um", material="unknown", model="tabulated")
- from_eps_csv(path, wavelength_unit="um", material="unknown", model="tabulated")
- epsilon(lambda_um)
- nk(lambda_um)
- table(lambda_um)

CSV expectations:
- n,k CSV requires wavelength + n + k columns.
- eps CSV requires wavelength + eps1 + eps2 columns.
- Accept wavelength column names: lambda_um, wavelength_um, lambda_nm, wavelength_nm only when unambiguous.
- Reference CSV files are user-provided. Do not extract or reproduce large tables from the PDFs.

Interpolation:
- Use scipy.interpolate.PchipInterpolator by default.
- No extrapolation by default. Raise ValueError outside validity range.

DataFrame table columns:
- lambda_um
- energy_eV
- eps1
- eps2
- n
- k
- alpha_m_inv
- alpha_cm_inv
- material
- model

Acceptance criteria:
- Synthetic CSV interpolation tests pass.
- Range error tests pass.
- Table column tests pass.
- data/reference/ge/README.md explains how a user can create local reference CSVs from legally available data, without redistributing PDF tables.
- pytest -q and ruff check pass.

At the end, report changed files and test results.
```

---

## P4 — Ge Frey Sellmeier model

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 4: Ge Frey Sellmeier model.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.
If needed, inspect pdf/Temperature-dependent refractive index of silicon and germanium.pdf to confirm the intended Frey/Leviton/Madison model form, transparent wavelength range, and temperature range.

Add:
- src/nkcalc/models/sellmeier.py
- src/nkcalc/materials/__init__.py
- src/nkcalc/materials/ge.py
- data/params/ge_frey_sellmeier.yml
- tests/test_frey_sellmeier_ge.py
- examples/02_ge_frey_sellmeier.py

Implement a temperature-dependent Sellmeier model:

n(lambda,T)^2 - 1 = sum_i S_i(T) * lambda^2 / (lambda^2 - lambda_i(T)^2)
S_i(T) = sum_j S_ij * T^j
lambda_i(T) = sum_j L_ij * T^j

Important:
- Do not invent exact Frey coefficients if they are not present in the repository.
- Do not copy large coefficient tables from the PDF into the repository.
- Create the YAML schema and loader.
- If the coefficient values are placeholders, clearly mark them as placeholder and make tests use synthetic coefficients.
- The model implementation must be ready to accept real Frey coefficients from a user-provided YAML.

Validity:
- For Ge Frey model, enforce 20 K <= T <= 300 K and 1.9 um <= lambda <= 5.5 um unless overridden explicitly.
- Default k=0 for this transparent-side model.
- Mark model name as "FreySellmeier".

Acceptance criteria:
- Synthetic coefficient tests pass.
- Validity range tests pass.
- table() returns lambda_um, energy_eV, eps1, eps2, n, k, alpha columns.
- The YAML records whether coefficients are real, user-provided, synthetic, or placeholder.
- pytest -q and ruff check pass.

At the end, report changed files, test results, which PDF(s) were consulted, and whether coefficients are placeholders or real.
```

---

## P5 — GeOpticalModel facade

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 5: Ge facade.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.

Update:
- src/nkcalc/materials/ge.py
- tests/test_ge_model.py
- examples/04_ge_compare_models.py

Implement GeOpticalModel as a facade over model backends.

Required constructors:
- GeOpticalModel.from_backend(backend, state=None)
- GeOpticalModel.tabulated_from_csv(path, wavelength_unit="um")
- GeOpticalModel.frey_sellmeier(temperature_K=295, params_path=None)
- Optionally add a helper for local Lumerical Ge CRC data only if it can be done without hard-coding data values.

Required methods:
- epsilon(lambda_um)
- nk(lambda_um)
- table(lambda_um)

Ge state metadata:
- material = "Ge"
- temperature_K
- strain_xx, strain_yy, strain_zz default 0
- electron_cm3, hole_cm3 default 0
- strain_state default "unstrained"
- source/reference metadata when using a tabulated backend

Rules:
- Do not duplicate eps/nk conversion logic.
- Use BaseOpticalModel interface.
- Preserve model metadata in output DataFrame.
- Treat bgdata/Ge (Germanium) - CRC.csv as optional local benchmark/reference data, not as model coefficients.
- Do not make tests require the local CSV unless the test is explicitly skipped when the file is absent.

Acceptance criteria:
- facade constructors work.
- table contains material/model/temperature metadata.
- tabulated_from_csv remains the primary path for user/local reference data.
- pytest -q and ruff check pass.

At the end, report changed files, test results, and whether bgdata was consulted.
```

---

## P6 — CLI and plotting

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 6: CLI and plotting.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.

Add/update:
- src/nkcalc/plotting/__init__.py
- src/nkcalc/plotting/plot_nk.py
- src/nkcalc/plotting/plot_alpha.py
- src/nkcalc/cli.py
- tests/test_cli_smoke.py

CLI commands:
1. nkcalc ge frey
   Options:
   - --lambda-min
   - --lambda-max
   - --num
   - --temperature
   - --params
   - --output
   - --lumerical
   - --plot

2. nkcalc table from-nk-csv
   Options:
   - path argument
   - --lambda-min
   - --lambda-max
   - --num
   - --output
   - --lumerical
   - --plot

Optional if clean and small:
3. nkcalc table from-lumerical-csv
   Options:
   - path argument, e.g. bgdata/Ge (Germanium) - CRC.csv
   - --output
   - --lumerical
   - --plot
   This command must explicitly map wavelength(m), Re(n_xx), Im(n_xx) to lambda_um, n, k.

Plot rules:
- Use matplotlib.
- Do not require GUI backend.
- Save to file if plot path is provided.
- Plot n and k vs lambda on one figure only if readable; otherwise implement separate helpers.

Acceptance criteria:
- CLI smoke tests create output files in tmp_path.
- Any bgdata/Lumerical CSV path is optional and must not make tests brittle.
- pytest -q and ruff check pass.

At the end, report changed files, test results, and whether bgdata was consulted.
```

---

## P7 — Adachi critical-point skeleton

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 7: Adachi critical-point skeleton.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.
If needed, inspect pdf/PhysRevB.38.12966.pdf to confirm the Adachi-style critical-point model structure and terminology. Use it for model architecture only unless the user explicitly provides approved parameter values.
Use bgdata/Ge (Germanium) - CRC.csv only as an optional comparison target for unstrained Ge n,k behavior, not as fitted CP parameters.

Add:
- src/nkcalc/models/critical_point.py
- src/nkcalc/models/adachi_ge.py
- data/params/ge_adachi_initial.yml
- tests/test_adachi_ge_skeleton.py
- examples/03_ge_adachi_skeleton.py

Goal:
Build a skeleton for a Ge critical-point dielectric model inspired by Adachi-style modeling. Do not claim full Adachi implementation unless all analytical terms are implemented and tested.

Implement:
- CriticalPoint dataclass
- CriticalPointModel base
- A generic damped oscillator / Lorentz-like term
- AdachiGeModel that reads YAML parameters and computes eps(lambda_um)
- metadata field indicating implemented_terms

YAML should include:
- eps_inf
- validity wavelength/energy range
- list of critical points with name, energy_eV, amplitude, gamma_eV, phase, kind
- flags for implemented terms

Rules:
- Placeholder parameters must be explicitly named placeholder/to_be_fitted.
- Do not embed large literature tables.
- Do not present generic Lorentz-like placeholder terms as a faithful full Adachi implementation.
- Include source_notes metadata that can name the relevant PDF/paper without claiming the placeholder parameters are literature values.
- If comparing to Lumerical/CRC bgdata, keep the comparison in examples/validation paths and do not bake the data into model defaults.
- The model must be useful as a scaffold for later fitting.

Acceptance criteria:
- YAML loader test passes.
- epsilon returns complex ndarray.
- table returns n,k,alpha columns.
- implemented_terms metadata is visible.
- pytest -q and ruff check pass.

At the end, report changed files, test results, which PDF(s) or bgdata were consulted, and which terms are placeholders.
```

---

## P8 — Drude model

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 8: Drude model.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.
Use the PDFs only for physical background or validation context unless approved carrier parameters are already present in data/params.
Use bgdata/Ge (Germanium) - CRC.csv only as a zero-carrier/unstrained baseline comparison if needed; do not infer Drude carrier parameters from it.

Add:
- src/nkcalc/models/drude.py
- data/params/ge_drude.yml
- tests/test_drude.py

Implement DrudeModel:
Delta eps_Drude(omega) = - sum_s omega_p,s^2 / (omega * (omega + i gamma_s))
omega_p,s^2 = N_s q^2 / (eps0 * m_s*)
gamma_s = q / (m_s* * mu_s)

Inputs:
- electron_cm3
- hole_cm3
- electron_effective_mass_rel
- hole_effective_mass_rel
- electron_mobility_cm2_Vs
- hole_mobility_cm2_Vs

Rules:
- Convert cm^-3 to m^-3.
- Convert cm^2/V/s to m^2/V/s.
- carrier density = 0 must return exactly zero delta eps array.
- No default high carrier density. Defaults should be zero.
- Effective masses and mobilities in YAML must be marked as user_provided, placeholder, or literature_checked.

Integrate optional Drude addition into GeOpticalModel if clean to do so; otherwise implement as standalone model first.

Acceptance criteria:
- zero-carrier test passes.
- nonzero carrier changes eps and increases long-wavelength loss qualitatively.
- unit conversion tests pass.
- pytest -q and ruff check pass.

At the end, report changed files, test results, which PDF(s) or bgdata were consulted if any, and which parameters are placeholders.
```

---

## P9 — Validation and model comparison

```text
Read AGENTS.md and EXECPLAN.md. Implement Phase 9: Validation hardening.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.
If needed, inspect the local PDFs to define validation metadata fields and relevant comparison regimes, but do not extract large tables from them.
Use bgdata/Ge (Germanium) - CRC.csv as the primary local Lumerical standard Ge unstrained n,k comparison source when present.

Add/update:
- src/nkcalc/core/validation.py
- src/nkcalc/plotting/compare_reference.py
- tests/test_validation.py

Implement:
- compare_tables(model_df, reference_df)
- compute_error_metrics(model_df, reference_df)
- save_validation_report(metrics, path)
- plot_model_vs_reference(model_df, reference_df, path)
- optional loader/helper for the Lumerical Ge CRC CSV if it belongs naturally in validation or IO

Metrics:
- RMSE_n
- RMSE_k
- MAE_n
- MAE_k
- RMSE_log_alpha where alpha > 0
- max_abs_error_n
- max_abs_error_k

Rules:
- Align on lambda_um using interpolation only when explicitly requested.
- If grids differ and interpolation is not requested, raise ValueError.
- Ge PD relevance: include weighted k/alpha metrics, but keep default weights transparent.
- Validation reports should preserve reference metadata such as material, source, temperature_K, wavelength_range_um, energy_range_eV, and notes.
- Reference data must come from user-provided CSV/YAML, not hidden extraction from the PDFs.
- Lumerical bgdata metadata should include source="Lumerical standard Ge CRC" and strain_state="unstrained".
- Do not copy bgdata rows into tests or examples; load the local file when explicitly requested or use synthetic fixtures.

Acceptance criteria:
- synthetic validation tests pass.
- report CSV or JSON is produced.
- comparison plot is saved in non-GUI environment.
- If bgdata is present, an example or optional smoke path can compare against it without making CI dependent on that file.
- pytest -q and ruff check pass.

At the end, report changed files, test results, and any PDF- or bgdata-derived validation assumptions that were used.
```

---

## P10 — Code review and hardening

```text
Read AGENTS.md, EXECPLAN.md, the "ローカルPDF文献の扱い" section, and the "ローカルLumerical標準データの扱い" section in PROMPTS.md. Perform a code review and hardening pass for nkcalc.

Scope:
- Do not add major new features.
- Improve docstrings, type hints, validation, error messages, tests.
- Check that units are explicit in names and docstrings.
- Check that extrapolation behavior is explicit.
- Check that placeholder coefficients are clearly marked.
- Check that no large copyrighted literature tables are embedded.
- Check that PDF-derived formulas, validity ranges, and source notes are represented honestly.
- Check that bgdata is treated as optional local benchmark/reference data, not silently baked into model coefficients.
- Check that Lumerical/CRC CSV column mappings and strain_state/source metadata are explicit wherever used.
- Check that Lumerical export writes correct lambda/n/k columns.

Run:
- pytest -q
- ruff check src tests examples

Deliver:
- concise summary of issues found
- changes made
- remaining risks
- test results
```

---

## P11 — Failure recovery prompt

```text
The previous implementation failed tests or produced errors.

Read the failing logs carefully. Do not rewrite unrelated parts of the repository.

Tasks:
1. Identify the minimal root cause.
2. Patch only the necessary files.
3. Add or adjust tests only if the existing test expectation is wrong.
4. Re-run pytest -q and ruff check src tests examples.
5. Report exactly what failed, what was changed, and the final test result.

If the failure involves bgdata/Ge (Germanium) - CRC.csv, keep the file optional unless the task explicitly requires local benchmark validation.

Do not introduce new physics models in this recovery step.
```

---

## P12 — Next phase planning: Si and SiGe

```text
Read AGENTS.md and EXECPLAN.md. Prepare a design-only plan for extending nkcalc from Ge to Si and SiGe.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.
If needed, inspect pdf/Si Temp Prameters.pdf, pdf/Temperature-dependent refractive index of silicon and germanium.pdf, and the broader Si/Ge PDFs for background.
Use bgdata/Ge (Germanium) - CRC.csv as an example of how local Lumerical standard benchmark files should be represented with metadata.

Do not implement yet.

Plan should cover:
- Si tabulated model using user-provided Green-style reference CSV
- Si transparent-side model options
- SiGe composition interpolation with bowing parameters
- strain_state handling: relaxed, pseudomorphic_on_Si, pseudomorphic_on_Ge, partially_relaxed
- API compatibility with GeOpticalModel
- validation strategy
- tests to add
- which local PDFs are relevant to each future model, and what must remain user-provided reference data
- how local Lumerical standard benchmark files under bgdata/ should be loaded, tagged, and excluded from hard-coded model parameters

Output the plan as docs/SI_SIGE_EXTENSION_PLAN.md.
```

---

## P13 — Reference CSV creation helper

```text
Read AGENTS.md and EXECPLAN.md. Implement a helper for users to create reference CSV files manually from their own legally available data.
Also read the "ローカルPDF文献の扱い" section in PROMPTS.md.
Also read the "ローカルLumerical標準データの扱い" section in PROMPTS.md.

Add:
- docs/REFERENCE_CSV_FORMAT.md
- examples/reference_csv_template_ge.csv
- examples/reference_csv_template_eps.csv
- optionally document the Lumerical/CRC CSV column mapping without copying rows

Rules:
- Do not extract or reproduce tables from PDFs.
- Do not copy rows from bgdata CSV into template CSVs.
- Provide column names and units.
- Provide a tiny synthetic example only, not real literature data.
- Explain that local PDFs may be used by the user as background/source material, but nkcalc expects the user to provide their own legally usable CSV/YAML data.
- Explain that local Lumerical/CRC CSV files can be converted by explicit column mapping: wavelength(m) * 1e6 -> lambda_um, Re(n_xx) -> n, Im(n_xx) -> k.

CSV formats:
1. nk format:
   lambda_um,n,k
2. eps format:
   lambda_um,eps1,eps2
3. optional metadata in sidecar YAML:
   material, reference, temperature_K, strain_state, notes

Acceptance criteria:
- Templates are tiny synthetic examples.
- Documentation explains how to use TabulatedModel.from_nk_csv and from_eps_csv.
- Documentation lists recommended metadata fields for source traceability without embedding PDF data.
- pytest -q and ruff check pass if code is changed.
```
