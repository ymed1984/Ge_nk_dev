# EXECPLAN.md — Ge/SiGe/Si `n,k` 計算パッケージ 実行計画

この実行計画は、Codexで `nkcalc` を段階実装するためのタスク分解である。最初の目標は Ge の MVP であり、Si/SiGe は後続拡張として扱う。

---

## 0. 成果物の定義

最終的に以下を作る。

```text
1. Python package: nkcalc
2. Ge intrinsic bulk model at 300 K
3. Tabulated n,k interpolation model
4. Ge transparent-side Sellmeier model
5. Lumerical FDTD sampled data export: lambda_um, n, k
6. Validation utilities against local reference CSV
7. Plot utilities for n, k, alpha, eps1, eps2
8. Later extensions: Drude, strain, Si, SiGe
```

---

## 1. 背景文献とローカルPDFの使い分け

| 文献 | ローカルPDF | 実装上の位置づけ | 実装タイミング |
|---|---|---|---|
| Aspnes & Studna, 1983 | `pdf/PhysRevB.27.985.pdf` | Si/Ge の `eps1, eps2, n, k, R, alpha` benchmark。1.5–6.0 eVの高エネルギー側検証。 | Phase 3以降の validation |
| Adachi, 1988 | `pdf/PhysRevB.38.12966.pdf` | Si/Ge の critical point 誘電関数モデル。Kramers–Kronig整合と CP項の理論骨格。 | Phase 7以降 |
| Frey, Leviton, Madison | `pdf/Temperature-dependent refractive index of silicon and germanium.pdf` | Si/Ge の温度依存 Sellmeier。Geは1.9–5.5 µm、20–300 Kの透明側 `n(λ,T)`。 | Phase 4 |
| Emminger et al., 2020 | `pdf/Temperaturedependent dielectricfunctionanddirectBandgapofGe.pdf` | Geの0.5–6.3 eV、10–738 Kの温度依存DF、E0/E0+Δ0の温度依存検証。 | Phase 7以降 |
| Green, 2008 | `pdf/Si Temp Prameters.pdf` | Siの300 K `alpha,n,k` と温度係数。 | Si拡張Phase |

重要: ローカルPDFは背景・式・用語・validity range・validation観点の確認に使う。文献表の大規模転載、PDF図からの長い数値トレース、係数表の直書きは避ける。reference data はユーザーがローカルCSV/YAMLとして用意する。実装では loader, validator, plotter を作る。

パラメータの扱い:

- 実文献値をリポジトリに入れる場合は、ユーザー提供の明示的な CSV/YAML として扱い、source metadata を持たせる。
- 係数が未確認なら `synthetic`, `placeholder`, `initial`, `to_be_fitted` を明記する。
- テストでは原則として synthetic data を使い、PDF由来の大きな数表に依存しない。
- 完了報告では、参照したPDF、PDFから確認した仕様、仮値またはユーザー提供待ちの値を記録する。

---

## 1.1 Lumerical標準モデル背景データ

`bgdata/` 配下に、Lumerical 標準モデル由来のローカル benchmark data を置く。

```text
bgdata/
  Ge (Germanium) - CRC.csv
```

確認済みの構造:

| ファイル | format | 主な列 | 想定用途 |
|---|---|---|---|
| `Ge (Germanium) - CRC.csv` | CSV | `wavelength(m)`, `Re(n_xx)`, `Im(n_xx)` | Ge, 歪みなし, Lumerical/CRC 標準 `n,k` benchmark |

扱い:

- Phase 5以降で、Ge facade、plot、CLI、validation、model comparison の背景比較として必要に応じて参照する。
- `Re(n_xx)` は `n`、`Im(n_xx)` は `k`、`wavelength(m) * 1e6` は `lambda_um` に明示変換する。
- metadata には `source="Lumerical standard Ge CRC"`、`strain_state="unstrained"` を残す。
- この CSV は物理モデル係数や critical-point fitting 初期値として暗黙利用しない。
- テストは基本 synthetic data を使う。実ファイルに触る検証は存在チェック付きの optional/smoke 扱いにする。
- rows を example CSV や test fixture に複製しない。

---

## 2. Phase一覧

| Phase | 名称 | 主目的 | 完了条件 |
|---:|---|---|---|
| 0 | Repository bootstrap | Python package骨格を作る | `pytest -q` が通る空プロジェクト |
| 1 | Core numerics | 単位・`eps/nk/alpha`変換 | round-trip testが通る |
| 2 | IO and export | CSV/Lumerical出力 | `lambda n k`出力が生成される |
| 3 | Tabulated model | 文献・測定値補間 | reference CSVを補間できる |
| 4 | Ge Frey Sellmeier | Ge透明側 `n(λ,T)` | validity rangeを守って計算できる |
| 5 | Ge facade | `GeOpticalModel` API統合 | Ge modelからtable/exportが可能 |
| 6 | Plot and CLI | 可視化とCLI | CLIからCSV/plot/exportが可能 |
| 7 | Adachi skeleton | critical point model骨格 | YAMLパラメータでepsを返す |
| 8 | Drude | FCA/Δn項 | carrier=0で不変、carrier>0で変化 |
| 9 | Validation hardening | 文献CSVとの比較 | RMSE/plot/reportを出せる |
| 10 | Si/SiGe extension | Si/SiGeへ展開 | Ge設計を再利用して拡張 |

---

## Phase 0 — Repository bootstrap

### 目的

`uv` または通常の `pip` で開発できる Python package を作る。

### 実装対象

```text
pyproject.toml
README.md
src/nkcalc/__init__.py
src/nkcalc/cli.py
tests/test_import.py
```

### `pyproject.toml` 基本仕様

```toml
[project]
name = "nkcalc"
version = "0.1.0"
description = "Optical n,k calculation tools for Ge, SiGe, and Si."
requires-python = ">=3.11"
dependencies = [
  "numpy>=1.26",
  "scipy>=1.11",
  "pandas>=2.0",
  "matplotlib>=3.8",
  "pyyaml>=6.0",
  "typer>=0.12",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.6",
]

[project.scripts]
nkcalc = "nkcalc.cli:app"

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Acceptance criteria

```bash
python -m pip install -e .[dev]
pytest -q
ruff check src tests
```

---

## Phase 1 — Core numerics

### 目的

全モデルで共通に使う物理定数・単位変換・`eps/nk/alpha` 変換を実装する。

### 実装対象

```text
src/nkcalc/constants.py
src/nkcalc/spectrum.py
src/nkcalc/core/nk.py
tests/test_units.py
tests/test_nk_conversion.py
tests/test_alpha_conversion.py
```

### 必須API

```python
wavelength_um_to_energy_ev(lambda_um)
energy_ev_to_wavelength_um(energy_ev)
energy_ev_to_omega_rad_s(energy_ev)
epsilon_to_nk(eps_complex)
nk_to_epsilon(n, k)
k_to_alpha_m_inv(k, lambda_um)
k_to_alpha_cm_inv(k, lambda_um)
alpha_cm_inv_to_k(alpha_cm_inv, lambda_um)
```

### 実装メモ

- `HC_EV_UM = 1.239841984` を使う。
- `epsilon_to_nk()` は受動媒質で `k >= 0` になるようにする。
- 複素平方根のブランチに注意する。

### Acceptance criteria

- `lambda -> E -> lambda` が相対誤差 `1e-12` 程度で戻る。
- `n,k -> eps -> n,k` が round trip する。
- `alpha = 4*pi*k/lambda` が正しく計算される。

---

## Phase 2 — IO and Lumerical export

### 目的

計算結果を CSV と Lumerical Sampled Data Material 用テキストに出力する。

### 実装対象

```text
src/nkcalc/io/csv_io.py
src/nkcalc/io/lumerical.py
tests/test_lumerical_export.py
examples/01_ge_tabulated_to_lumerical.py
```

### 出力形式

Lumerical用はデフォルトでヘッダなし3列にする。

```text
lambda_um    n    k
```

オプションで `wavelength_unit="nm"` を許可するが、内部標準は `um` とする。

### Acceptance criteria

- DataFrameから `lambda_um,n,k` を抽出してtxt出力できる。
- `header=False` がデフォルト。
- NaN/infがある場合は例外を出す。
- `k < 0` は原則エラー。ただし明示オプションで許可可能にする。

---

## Phase 3 — Tabulated model

### 目的

文献・測定データから `n,k` または `eps1,eps2` を読み、任意波長gridへ補間する。

### 実装対象

```text
src/nkcalc/models/base.py
src/nkcalc/models/tabulated.py
src/nkcalc/core/validation.py
tests/test_tabulated_model.py
data/reference/ge/README.md
```

### 必須API

```python
class BaseOpticalModel:
    def epsilon(self, lambda_um: np.ndarray) -> np.ndarray: ...
    def nk(self, lambda_um: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
    def table(self, lambda_um: np.ndarray) -> pd.DataFrame: ...

class TabulatedModel(BaseOpticalModel):
    @classmethod
    def from_nk_csv(cls, path: str, *, wavelength_unit: str = "um") -> "TabulatedModel": ...
    @classmethod
    def from_eps_csv(cls, path: str, *, wavelength_unit: str = "um") -> "TabulatedModel": ...
```

### 補間仕様

- 基本は `scipy.interpolate.PchipInterpolator` を使う。
- `n,k` を直接補間するモードと、`eps1,eps2` を補間するモードを分ける。
- 範囲外 extrapolation はデフォルト禁止。

### Acceptance criteria

- sample CSVを読み込み、任意gridで `table()` を返す。
- 入力範囲外は `ValueError`。
- `eps` と `n,k` の列が整合する。
- `data/reference/ge/README.md` に、reference CSV はユーザーが合法的に用意すること、PDF表を同梱しないことを書く。

---

## Phase 4 — Ge Frey Sellmeier model

### 目的

Ge の 1.9–5.5 µm、20–300 K 透明側 `n(λ,T)` を返す Sellmeier model を実装する。

### 実装対象

```text
src/nkcalc/models/sellmeier.py
src/nkcalc/materials/ge.py
data/params/ge_frey_sellmeier.yml
tests/test_frey_sellmeier_ge.py
examples/02_ge_frey_sellmeier.py
```

### モデル式

温度依存Sellmeierを以下の形で実装する。

```text
n(lambda,T)^2 - 1 = sum_i S_i(T) * lambda^2 / (lambda^2 - lambda_i(T)^2)

S_i(T)      = sum_j S_ij * T^j
lambda_i(T)= sum_j L_ij * T^j
```

### 注意

- FreyのGeモデルは透明側 `n` 用である。
- O/C-band吸収端の `k` をこのモデルで生成してはならない。
- デフォルトでは `k=0` とするが、出力に `model="FreySellmeier"` と明記する。
- 必要に応じて `pdf/Temperature-dependent refractive index of silicon and germanium.pdf` でモデル形と適用範囲を確認する。
- Frey係数をPDFからそのまま埋め込まない。まず YAML schema と loader を作り、係数が仮値なら `synthetic` または `placeholder` と metadata に明記する。

### Acceptance criteria

- validity range: `20 <= T <= 300`, `1.9 <= lambda_um <= 5.5`。
- 範囲外は `ValueError`。
- 出力shapeが入力shapeと一致する。
- `table()` が `eps1, eps2, n, k, alpha` を返す。
- `ge_frey_sellmeier.yml` は係数の provenance を表す field を持つ。

---

## Phase 5 — Ge facade

### 目的

ユーザーが `GeOpticalModel` から一貫して `table`, `nk`, `epsilon`, `export` を使えるようにする。

### 実装対象

```text
src/nkcalc/materials/ge.py
tests/test_ge_model.py
examples/04_ge_compare_models.py
```

### API案

```python
ge = GeOpticalModel.frey_sellmeier(temperature_K=295)
df = ge.table(lambda_um)

ge_tab = GeOpticalModel.tabulated_from_csv("reference/ge/my_ge.csv")
df = ge_tab.table(lambda_um)
```

### Acceptance criteria

- Ge modelが `BaseOpticalModel` と同じ interface を持つ。
- Lumerical exportへ直接渡せる DataFrame を返す。
- model名、temperature、validity infoがDataFrameに入る。
- tabulated backend は local/user reference data の metadata を保持する。
- `bgdata/Ge (Germanium) - CRC.csv` は必要に応じて Ge unstrained benchmark として参照可能にするが、facade の必須依存にはしない。

---

## Phase 6 — Plot and CLI

### 目的

CLIからデータ生成、plot、Lumerical exportを行えるようにする。

### 実装対象

```text
src/nkcalc/plotting/plot_nk.py
src/nkcalc/plotting/plot_alpha.py
src/nkcalc/cli.py
tests/test_cli_smoke.py
```

### CLI例

```bash
nkcalc ge frey \
  --lambda-min 1.9 \
  --lambda-max 5.5 \
  --num 301 \
  --temperature 295 \
  --output ge_frey_295K.csv \
  --lumerical ge_frey_295K_lumerical.txt
```

```bash
nkcalc table from-nk-csv reference/ge/my_ge.csv \
  --lambda-min 1.2 \
  --lambda-max 1.7 \
  --num 501 \
  --output ge_tabulated.csv \
  --lumerical ge_tabulated_lumerical.txt
```

### Acceptance criteria

- CLIからCSVとLumerical txtを生成できる。
- plot保存オプションを持つ。
- CI/非GUI環境でも動作する。
- Lumerical/CRC CSV を扱う CLI を追加する場合は、列対応 `wavelength(m) * 1e6 -> lambda_um`, `Re(n_xx) -> n`, `Im(n_xx) -> k` を明示し、実ファイル不在でテストが壊れないようにする。

---

## Phase 7 — Adachi critical-point skeleton

### 目的

Adachi型モデルの全体構造を作る。最初から完全実装しようとせず、項別に追加できる skeleton とする。

### 実装対象

```text
src/nkcalc/models/critical_point.py
src/nkcalc/models/adachi_ge.py
data/params/ge_adachi_initial.yml
tests/test_adachi_ge_skeleton.py
examples/03_ge_adachi_skeleton.py
```

### 最初に実装するもの

- `CriticalPoint` dataclass
- `CriticalPointModel` base
- Lorentz/DHO-like term
- YAML parameter loader
- `eps_inf` + oscillator sum
- `implemented_terms` と `source_notes` metadata

### 後で追加するもの

- E0/E0+Δ0 3D M0 項
- E1/E1+Δ1 項
- E2 DHO + 2D M2 mixture
- E0' triplet DHO
- 温度依存 broadening / energy shift

### Acceptance criteria

- YAMLからモデルを構築できる。
- `epsilon(lambda_um)` が complex ndarray を返す。
- 仮パラメータを `placeholder` と明記する。
- `Adachi` という名前であっても未実装項を正確に表示する。
- `pdf/PhysRevB.38.12966.pdf` は構造確認に使い、未実装項や仮パラメータを実文献値として扱わない。
- `bgdata/Ge (Germanium) - CRC.csv` は unstrained Ge の比較先としてのみ扱い、CPパラメータとして暗黙に使わない。

---

## Phase 8 — Drude model

### 目的

ドーピング・注入キャリアによる自由キャリア吸収と屈折率変化を扱う。

### 実装対象

```text
src/nkcalc/models/drude.py
data/params/ge_drude.yml
tests/test_drude.py
```

### モデル式

```text
Delta eps_Drude(omega) = - sum_s omega_p,s^2 / (omega * (omega + i gamma_s))
omega_p,s^2 = N_s q^2 / (eps0 * m_s*)
gamma_s = q / (m_s* * mu_s)
```

### Acceptance criteria

- `electron_cm3=hole_cm3=0` で `Delta eps = 0`。
- carrier densityを上げると長波長側で `k` が増える。
- 有効質量・移動度の単位変換がテストされる。
- `ge_drude.yml` の有効質量・移動度には `user_provided`, `literature_checked`, `placeholder` などの provenance を持たせる。
- zero-carrier/unstrained baseline comparison に bgdata を使う場合でも、Drude パラメータは bgdata から推定しない。

---

## Phase 9 — Validation hardening

### 目的

reference CSVに対してモデル誤差を定量化し、plot/reportを出す。

### 実装対象

```text
src/nkcalc/core/validation.py
src/nkcalc/plotting/compare_reference.py
tests/test_validation.py
```

### 評価指標

```text
RMSE_n
RMSE_k
MAE_n
MAE_k
weighted_RMSE_k
RMSE_log_alpha
max_abs_error_n
max_abs_error_k
```

Ge PD用途では、`k` と `alpha` の誤差を重く見る。

### Acceptance criteria

- model table と reference table を同一gridで比較できる。
- report CSVを出力できる。
- `n,k,alpha` 比較plotを保存できる。
- report には `material`, `source`, `temperature_K`, `wavelength_range_um`, `energy_range_eV`, `notes` などの metadata を残せる。
- reference data はユーザー提供CSV/YAMLから読み、PDFから隠れて抽出しない。
- `bgdata/Ge (Germanium) - CRC.csv` を local Lumerical standard benchmark として読み込める場合、metadata に `source="Lumerical standard Ge CRC"` と `strain_state="unstrained"` を残す。
- bgdata の実数値 rows は test fixture や example CSV に複製しない。

---

## Phase 10 — Si/SiGe extension

### 目的

Ge MVPを壊さず、SiとSiGeへ拡張する。

### Si実装方針

- Green 2008を validation source として扱う。
- 0.25–1.45 µmの `alpha,n,k` table loaderを作る。
- 透明側の分散式・温度係数は後続で追加する。
- `pdf/Si Temp Prameters.pdf` と `pdf/Temperature-dependent refractive index of silicon and germanium.pdf` は背景確認に使うが、表データはユーザー提供CSVにする。

### SiGe実装方針

最初は以下の bowing 補間を導入する。

```text
P_SiGe(x) = (1-x) P_Si + x P_Ge - b_P x(1-x)
```

ただし、SiGeの `n,k` は単純補間で完結しない。critical-point energy、broadening、strain stateを明示する設計にする。

### Acceptance criteria

- Ge APIと同じ `BaseOpticalModel` interfaceでSi/SiGeを扱える。
- SiGeでは `Ge_fraction`, `strain_state`, `temperature_K` を必須メタデータにする。
- Si/SiGe 用の reference data と model parameter は、provenance を metadata として保持する。
- bgdata のような Lumerical 標準 benchmark file は、材料・歪み状態・source metadata を明示する local reference として扱う設計にする。

---

## 3. 推奨実行順序

Codexへは、以下の順で依頼する。

```text
P0: Repository bootstrap
P1: Core numerics
P2: IO and Lumerical export
P3: Tabulated model
P4: Ge Frey Sellmeier
P5: Ge facade
P6: CLI and plotting
P7: Adachi skeleton
P8: Drude model
P9: Validation hardening
P10: Review and refactor
P11: Failure recovery when needed
P12: Si/SiGe design plan
P13: Reference CSV creation helper
```

---

## 4. 完成時の最小デモ

```python
import numpy as np
from nkcalc.materials.ge import GeOpticalModel
from nkcalc.io.lumerical import export_lumerical_nk_txt

lambda_um = np.linspace(1.9, 5.5, 301)

ge = GeOpticalModel.frey_sellmeier(temperature_K=295)
df = ge.table(lambda_um)

df.to_csv("ge_295K.csv", index=False)
export_lumerical_nk_txt(df, "ge_295K_lumerical.txt")
```

期待される `ge_295K_lumerical.txt`:

```text
1.900000    4.xxxxxx    0.000000
1.912000    4.xxxxxx    0.000000
...
```

---

## 5. 実装完了時レポート形式

Codexは各タスク完了時に以下を報告する。

```text
Summary:
- 実装した内容

Changed files:
- path/to/file.py
- path/to/test.py

Tests:
- pytest -q: PASS/FAIL
- ruff check: PASS/FAIL

Notes:
- 参照したPDF
- 参照したbgdata
- 未実装項
- 仮パラメータ
- ユーザー提供CSV/YAMLが必要なデータ
- 次に実装すべきこと
```
