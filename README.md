# Fraud Analytics

**An end-to-end study of synthetic travel-expense fraud: data controls, statistical screening, machine learning and relationship analysis.**

By **Kyaw Thiha (Kendrick)** · ITCY514, Fraud Analysis and Detection · Mahidol University.

Finance teams need to distinguish suspicious reimbursements from ordinary business variation and data errors. This project explores that problem through **Aster Field Services**, a fictional company. It combines two course projects in one repository: a midterm rules-and-statistics pipeline and a final Python experiment that compares those rules with supervised models.

## At a glance

| | Midterm | Final |
|---|---|---|
| Scenario | Fictional 2026 travel reimbursements | Expanded fictional 2025 expense case |
| Input | 176 raw claim rows across three tables | 4,812 raw claim rows across five tables |
| Valid claims | 169 | 4,800 |
| Quarantine | 7 claim rows and 2 master records | 12 claim rows |
| Methods | Reconciliation, policy and relationship rules, robust scores, Welch comparisons and breakpoint screening | Logistic regression, Random Forest, FP-Growth and graph analysis |
| Runtime | Node.js 22+; optional n8n/PostgreSQL | Python 3.12; optional Jupyter |
| Start here | [Midterm guide](midterm/README.md) | [Final guide](final/README.md) |

The stages use different synthetic ledgers and years. They show progression in methods and should be analyzed separately.

## Main result

The final experiment fixes preprocessing, thresholds and model selection before evaluating an **800-claim test set containing 60 planted fraud cases**.

| Method | True positives | False alarms | Missed fraud | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Existing rules | 24 | 35 | 36 | 40.7% | 40.0% | 0.403 |
| Logistic regression | 48 | 21 | 12 | 69.6% | 80.0% | 0.744 |
| Random Forest | 44 | 12 | 16 | 78.6% | 73.3% | 0.759 |

Random Forest was selected using **validation F1**, not these test results. Its test average precision is **0.806**. Logistic regression finds more planted fraud, with more false alarms. Under subtler simulated inflation in November–December, Random Forest recall falls to **58.3%**.

![Model comparison on synthetic test claims](final/reports/figures/model_comparison.png)

These measurements describe this synthetic experiment. They do not establish real-world detection performance, intent or confirmed financial loss.

## How the analysis works

1. **Acquire and validate.** Preserve source tables; check identifiers, dates, numeric values and relationships; retain invalid records in quarantine.
2. **Reconcile.** Verify that source counts and numeric amounts equal production plus quarantine before analysis proceeds.
3. **Screen expenses.** Examine reused receipts, self-approval, policy allowances, account links and unusual amounts.
4. **Engineer history.** Compute prior receipt reuse, claim frequency and merchant concentration using only earlier records.
5. **Train and evaluate.** Fit on January–June, select thresholds on July–August, test on September–October and check November–December separately.
6. **Explain and investigate.** Inspect coefficients, validation permutation importance, false alarms, missed cases, associations and observed graph paths.

The final classifiers exclude claim IDs, employee IDs, merchant IDs and planted labels. Graph construction and FP-Growth use training records without fraud labels; graph features are not fed into the classifiers.

## Quick start

```sh
git clone https://github.com/1NC0GN1T0-K3N/fraud-analytics.git
cd fraud-analytics
```

**Read without installing:** open the [final notebook](final/Fraud_Analytics.ipynb), [model metrics](final/reports/model_metrics.csv), [midterm findings](midterm/results/findings.json), or the guides below. The notebook is committed with outputs cleared; the saved figures and tables provide the numerical evidence.

**Run the midterm without external services:**

```sh
node --test midterm/tools/pipeline.test.mjs
node midterm/tools/run_analysis.mjs
```

**Run the final analysis with Python 3.12:**

```sh
cd final
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/project_core.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead. On systems where Python is named `python3`, use that command to create the environment.

For an interactive notebook, install `requirements-notebook.txt` instead of `requirements.txt`, then run `jupyter lab Fraud_Analytics.ipynb` from `final/`. See the [final guide](final/README.md) for output locations and commands to regenerate figures.

## Repository layout

```text
midterm/
  data/                 Three synthetic source CSVs
  case_config.json      Policy, mappings and analytical settings
  tools/                Offline runner, shared core and original tests
  workflow/             Deterministic and optional Gemini n8n exports
  results/              Saved offline findings
final/
  data/landing/         Five synthetic source CSVs
  data/production/      Valid claim export
  tools/                Generator, controls, models, graph and figure code
  Fraud_Analytics.ipynb Step-by-step analytical notebook
  reports/              Metrics, features, associations, graphs and figures
  requirements*.txt     Core and notebook dependencies
docs/DATA_DICTIONARY.md  Source fields, features and output interpretation
VALIDATION.md            Checks performed and verification limits
NOTICE.md                Attribution and public-release scope
```

## Reproducibility and limitations

The final experiment uses a fixed seed and pinned analytical packages. Generated model binaries, synthetic answer keys, virtual environments and notebook reruns are ignored by Git and can be recreated from the included code. The [data dictionary](docs/DATA_DICTIONARY.md) explains source fields and predictors.

This is one generator and one seed. Entities overlap across time partitions; the experiment does not establish performance on new organizations, unseen employees or unrelated fraud schemes. Scores are uncalibrated. Shared merchants, graph communities and high-lift associations are investigation leads that can also reflect legitimate activity. Midterm peer comparisons use an exploratory scan-selected window, which limits statistical inference.

Optional n8n/PostgreSQL/Gemini integration requires the reader's own configuration. Offline results and Python execution are verified separately from live integration; see [validation](VALIDATION.md).

## Authorship and scope

This repository contains the author's expense-case implementation and analytical results. Peer submissions, peer-review reports and class role-play verdicts are excluded. No independent peer-review outcome is claimed. All identities, accounts and financial records are fictitious.

AI assisted implementation and writing; the code computes the results. See [NOTICE.md](NOTICE.md) for attribution and reuse scope.
