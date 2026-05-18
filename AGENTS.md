# AGENTS.md — `nkcalc` Codex 実装指示

このファイルは、`nkcalc` リポジトリで Codex が作業するときの常駐指示である。目的は、Ge → Si → SiGe の順に、光シミュレーション用の `n(λ), k(λ)` を生成・検証・Lumerical FDTDへ出力できる Python パッケージを段階実装することにある。

---

## 1. プロジェクト目的

`nkcalc` は、以下を満たす Python パッケージとして実装する。

- Ge, Si, SiGe の複素屈折率 `n + i k` を生成する。
- 基本変数は `n,k` ではなく、複素誘電率 `eps = eps1 + 1j * eps2` とする。
- 文献・測定データの補間モデル、Sellmeier モデル、critical-point 誘電関数モデル、Drude 自由キャリア項、歪み・温度補正へ拡張可能な構成にする。
- Lumerical FDTD の Sampled Data Material に投入しやすい `lambda_um, n, k` の3列テキストを出力する。
- すべてのモデルに validity range を持たせ、範囲外 extrapolation を暗黙に行わない。

---

## 2. 実装優先順位

まず Ge の MVP を完成させる。Si/SiGe は拡張フェーズであり、Ge MVP の設計を壊してまで先に実装しない。

優先順位は以下である。

1. 単位変換、`eps <-> n,k`、`k <-> alpha` の基礎関数
2. `TabulatedModel` による文献・測定値補間
3. CSV/Lumerical出力
4. Ge 用 `FreySellmeierModel`
5. Ge 用 `GeOpticalModel` facade
6. plot と validation utility
7. Ge 用 `AdachiCriticalPointModel` skeleton
8. Drude 項
9. 歪み・温度・Si/SiGe 拡張

---

## 3. 物理モデル上の基本ルール

### 3.1 複素誘電率を基準にする

モデルは原則として以下を返す。

```python
eps: np.ndarray  # complex dielectric function
```

`n,k` は派生量として計算する。

```text
eps = eps1 + i eps2
n_complex = n + i k = sqrt(eps)
alpha = 4*pi*k/lambda
```

### 3.2 波長・エネルギー・周波数の単位を明示する

コード内では、以下の単位を固定する。

| 量 | 変数名 | 単位 |
|---|---|---|
| 波長 | `lambda_um` | µm |
| エネルギー | `energy_eV` | eV |
| 角周波数 | `omega_rad_s` | rad/s |
| 吸収係数 | `alpha_cm_inv`, `alpha_m_inv` | cm^-1, m^-1 |
| キャリア密度 | `electron_cm3`, `hole_cm3` | cm^-3 |
| 移動度 | `mobility_cm2_Vs` | cm^2/V/s |

単位の暗黙変換は禁止する。関数名・docstring・テストで単位を明記する。

### 3.3 Ge の O-band/C-band は吸収端材料として扱う

Ge の 1.2–1.7 µm は直接遷移端近傍のため、透明材料用 Sellmeier だけで扱わない。MVP では、以下を分ける。

- `TabulatedModel`: 測定値・文献値の補間。最初の比較基準。
- `FreySellmeierModel`: 1.9–5.5 µm の透明側 `n(λ,T)` 用。
- `AdachiCriticalPointModel`: 吸収端・critical point を含む誘電関数モデル。
- `DrudeModel`: ドーピング・注入キャリアによる `Δeps`。

### 3.4 データ再配布に注意する

PDF中の大きな表をそのままソースコードやリポジトリに埋め込まない。reference CSV はユーザーがローカルで用意する前提にする。実装側は、CSV/YAML を読み込む loader と validation pipeline を提供する。

### 3.5 ローカルPDFは背景確認に使う

`pdf/` 配下の論文PDFは、モデル式、定義、適用範囲、温度範囲、validation 観点を確認するための背景資料として扱う。PDFから大きな表・係数表・図の数値トレース結果をコード、テスト、CSV、YAMLへそのまま転載しない。

文献由来の係数を実装値として扱うのは、以下のいずれかを満たす場合に限る。

- リポジトリ内に、ユーザーが用意した明示的な YAML/CSV がある。
- ユーザーがその場で、特定の値を使うよう明示した。
- 値が小規模な式定義・物理定数・モデル構造の説明に必要な範囲であり、かつ出典を metadata に残す。

未確認または仮の数値は、`placeholder`, `synthetic`, `initial`, `to_be_fitted` のいずれかを、ファイル名・キー名・コメント・metadata の少なくとも一箇所に明記する。実装完了時の報告では、参照したPDF、実文献値ではない仮値、ユーザー提供データが必要な箇所を明記する。

---

## 4. 参照文献の役割

以下の文献名は、モデル設計・validation の背景として使う。大きな数表を丸ごと転載しない。

| 文献 | ローカルPDF | 実装での使い方 |
|---|---|---|
| Aspnes & Studna, 1983 | `pdf/PhysRevB.27.985.pdf` | Si/Ge の `eps1, eps2, n, k, R, alpha` の高エネルギー側 benchmark 背景。数表はユーザー提供CSVとして扱う。 |
| Adachi, 1988 | `pdf/PhysRevB.38.12966.pdf` | Si/Ge の critical-point 誘電関数モデルの中核。まず skeleton、次に項別実装。パラメータは仮値またはユーザー提供YAMLにする。 |
| Frey, Leviton, Madison | `pdf/Temperature-dependent refractive index of silicon and germanium.pdf` | Si/Ge の温度依存 Sellmeier。Ge は 1.9–5.5 µm、20–300 K の透明側 `n` 用。係数は無断転載せず、YAML schema と loader を先に作る。 |
| Emminger et al., 2020 | `pdf/Temperaturedependent dielectricfunctionanddirectBandgapofGe.pdf` | Ge の温度依存 DF と E0/E0+Δ0 の温度依存 validation 背景。reference data はユーザー提供CSVにする。 |
| Green, 2008 | `pdf/Si Temp Prameters.pdf` | Si 拡張時の 300 K `alpha,n,k` と温度係数 validation 背景。表データはユーザー提供CSVにする。 |

---

## 5. リポジトリ構成

基本構成は以下とする。

```text
nkcalc/
  README.md
  AGENTS.md
  EXECPLAN.md
  PROMPTS.md
  pyproject.toml

  pdf/
    PhysRevB.27.985.pdf
    PhysRevB.38.12966.pdf
    Temperature-dependent refractive index of silicon and germanium.pdf
    Temperaturedependent dielectricfunctionanddirectBandgapofGe.pdf
    Si Temp Prameters.pdf

  src/
    nkcalc/
      __init__.py
      constants.py
      spectrum.py

      core/
        __init__.py
        nk.py
        validation.py
        warnings.py

      models/
        __init__.py
        base.py
        tabulated.py
        sellmeier.py
        critical_point.py
        adachi_ge.py
        drude.py
        strain.py

      materials/
        __init__.py
        ge.py
        si.py
        sige.py

      io/
        __init__.py
        csv_io.py
        yaml_io.py
        lumerical.py

      plotting/
        __init__.py
        plot_nk.py
        plot_alpha.py
        compare_reference.py

      cli.py

  data/
    params/
      ge_frey_sellmeier.yml
      ge_adachi_initial.yml
      ge_drude.yml
    reference/
      ge/
        README.md
        placeholder_ge_reference.csv
      si/
        README.md

  examples/
    01_ge_tabulated_to_lumerical.py
    02_ge_frey_sellmeier.py
    03_ge_adachi_skeleton.py
    04_ge_compare_models.py

  tests/
    test_units.py
    test_nk_conversion.py
    test_alpha_conversion.py
    test_tabulated_model.py
    test_frey_sellmeier_ge.py
    test_lumerical_export.py
    test_cli_smoke.py
```

---

## 6. コード品質ルール

- Python 3.11 以上を対象にする。
- `numpy`, `scipy`, `pandas`, `matplotlib`, `pyyaml`, `typer`, `pytest`, `ruff` を基本依存とする。
- すべての public 関数に docstring を付ける。
- array 入力は `np.asarray(..., dtype=float)` で正規化する。
- validity range 外の入力は、原則として `ValueError` または明示 warning を出す。
- CLI は失敗時に例外を握りつぶさない。
- テストなしの機能追加は禁止する。
- 数式の符号、単位、ブランチ選択はテストで固定する。
- plot 関数は図を返すか保存する。勝手に GUI 表示しない。

---

## 7. テスト方針

最低限、以下を実装・維持する。

| テスト | 内容 |
|---|---|
| `test_units.py` | `lambda_um <-> energy_eV`, `energy_eV -> omega_rad_s` |
| `test_nk_conversion.py` | `eps -> n,k -> eps` の round trip |
| `test_alpha_conversion.py` | `k -> alpha -> k` の round trip |
| `test_tabulated_model.py` | interpolation, 範囲外エラー |
| `test_frey_sellmeier_ge.py` | validity range, 温度依存 shape, 出力 shape |
| `test_lumerical_export.py` | 3列 `lambda n k` 出力、ヘッダ有無、単位 |
| `test_cli_smoke.py` | CLIがCSV/Lumerical出力を作る |

テスト実行コマンド:

```bash
pytest -q
ruff check src tests examples
```

---

## 8. 実装時の禁止事項

- 文献PDFの表を大量にコードへ直書きしない。
- PDFや図から抽出した長い数値列を、テスト fixture や example CSV として同梱しない。
- Ge O/C-band を Sellmeier のみで完結させない。
- 単位が不明な関数名・引数名を作らない。
- validity range 外を silent extrapolation しない。
- Lumerical export で `k` の符号を曖昧にしない。受動媒質では `k >= 0` を原則にする。
- `n,k` と `eps1,eps2` の変換式を複数箇所に重複実装しない。
- 未検証の数値パラメータを「正確な文献値」として扱わない。仮値は `synthetic`, `initial`, `placeholder`, `to_be_fitted` を明記する。

---

## 9. 作業フロー

1. 作業前に `EXECPLAN.md` の該当 phase を確認する。
2. 実装する prompt は `PROMPTS.md` から選ぶ。
3. 必要に応じて `pdf/` の該当PDFを参照し、式・validity・用語を確認する。
4. PDFを参照した場合は、参照目的と、コードへ取り込んだ値が仮値か実値かを記録する。
5. 変更対象ファイルを最小化する。
6. 実装後に `pytest -q` と `ruff check` を実行する。
7. 失敗した場合は、失敗ログと修正方針を短くまとめてから修正する。
8. 完了時は、変更ファイル、実装内容、実行したテスト、参照したPDF、仮パラメータ、未解決事項を報告する。
