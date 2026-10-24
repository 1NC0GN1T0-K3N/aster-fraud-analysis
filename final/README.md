# Final project — supervised fraud analytics

The final stage asks whether supervised models detect synthetic expense-fraud patterns missed by rules while limiting false alarms. Aster Field Services is fictional; the ledger, policies, entities and evaluation labels are generated locally.

## Included artifacts

| Artifact | Purpose |
|---|---|
| [Fraud_Analytics.ipynb](Fraud_Analytics.ipynb) | Full explanatory notebook with readable stages and error examples |
| [tools/project_core.py](tools/project_core.py) | Deterministic generator, validation, features, fitting, evaluation and associations |
| [tools/graph_analysis.py](tools/graph_analysis.py) | Training-only profiles, centralities, communities and observed paths |
| [tools/build_graph_outputs.py](tools/build_graph_outputs.py) | Graph figure helper used by the notebook |
| [tools/render_figures.py](tools/render_figures.py) | Regenerate the four committed analytical charts from saved reports |
| [data/landing/](data/landing/) | Five source tables, including deliberate invalid claims |
| [reports/](reports/) | Saved metrics, scores, features, association rules, graph evidence and plots |

## Environment and execution

Use **Python 3.12** with the pinned packages in [requirements.txt](requirements.txt). From this directory:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/project_core.py
python tools/render_figures.py
```

Windows PowerShell activation: `.venv\Scripts\Activate.ps1`. The command-line pipeline regenerates `data/landing/`, `data/production/` and analytical reports **in this directory**. The figure command then refreshes the saved plots. Use a separate checkout if you want to preserve a different experiment.

For the notebook interface:

```sh
python -m pip install -r requirements-notebook.txt
jupyter lab Fraud_Analytics.ipynb
```

Open the notebook and run its cells in order. It works from `final/` or the repository root and writes regenerated evidence under `final/notebook_run/`, preserving the committed data and reports. It requires the companion `tools/` directory. No n8n, database or external AI account is needed.

The pipeline creates `private/ground_truth.csv`, private prediction/evaluation files, and fitted models in `models/`. They are synthetic, generated artifacts and are ignored by Git. They are not missing download dependencies. The notebook creates equivalents inside `notebook_run/`.

## Data and evaluation design

Five tables cover employees, merchants, trips, approvals and expense claims. **4,812 raw claim rows reconcile to 4,800 valid and 12 quarantined rows**. One nonnumeric amount is retained in quarantine and excluded from numeric control totals. See the [data dictionary](../docs/DATA_DICTIONARY.md).

| Split | Fictional 2025 months | Claims | Planted fraud | Use |
|---|---|---:|---:|---|
| Training | January–June | 2,400 | 176 | Fit preprocessing and models |
| Validation | July–August | 800 | 61 | Choose thresholds and model |
| Test | September–October | 800 | 60 | Fixed final comparison |
| Later period | November–December | 800 | 60 | Evaluate subtler simulated inflation |

Scoring occurs **after approval and before reimbursement**. Historical features look backward. Transforms fit only on training data, related receipt groups remain within one split, and private labels/IDs are excluded from classifier predictors. Labels are planted by the case scenarios rather than inferred from detection rules.

Logistic regression uses standardized numeric variables, one-hot categories, balanced class weights and `C=1`. Random Forest uses 240 trees, maximum depth 9, minimum leaf size 8, `max_features=0.8` and balanced subsample weights. A predefined 0.05–0.95 threshold grid is evaluated on validation F1, with precision and the higher threshold resolving ties. The selected models are not refitted after validation.

## Results

| Method | Test TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Existing rules | 24 | 35 | 36 | 40.7% | 40.0% | 0.403 |
| Logistic regression | 48 | 21 | 12 | 69.6% | 80.0% | 0.744 |
| Random Forest | 44 | 12 | 16 | 78.6% | 73.3% | 0.759 |

Random Forest was selected on validation F1. Its test average precision is **0.806**; its later-period recall falls to **58.3%**. The all-legitimate accuracy baseline is 92.5% and detects no fraud, so accuracy is not the headline measure.

![Test precision–recall performance](reports/figures/precision_recall.png)

FP-Growth discovers five training associations using minimum support 0.004, confidence 0.20, lift 2 and itemset length at most 3. Each basket contains an employee, merchant and approver. A disclosed legitimate employee–merchant relationship is retained as a negative control.

The training affiliation graph has 147 observed nodes, 1,703 distinct employee–merchant links and nine communities. It uses degree, normalized unweighted betweenness and claim-count-weighted greedy modularity. The selected seven-node view omits other observed links. Community membership is computed on the full graph; shared merchants and paths do not prove collusion. No graph predictor enters the classifiers.

![Observed relationship graph](reports/figures/graph_relationships.png)

## Output guide

- `model_metrics.csv`: confusion counts, thresholds, precision, recall, F1 and average precision by model and period.
- `claim_scores.csv`: published claim-level review scores without private labels or full account values.
- `features.csv`: actual predictor values and rule alerts.
- `reconciliation.json` and `quarantine.csv`: data-control evidence and rejected claims.
- `logistic_coefficients.csv`: standardized coefficients and odds ratios, not causal effects.
- `rf_permutation_importance.csv`: mean decrease in validation average precision when a predictor is shuffled.
- `association_rules.csv`: discovered training relationships and persistence in later periods.
- `graph_*.csv` and `graph_analysis.json`: observed links, node measures, communities and claim provenance.
- `training_*`: descriptive training profiles; robust outliers are not automatically fraud labels.
- `results.json` and `pr_curves.json`: machine-readable experiment summary and curve values.

## Limits and validation

One synthetic generator, one seed and recurring entities limit external validity. Scores are not calibrated real-world probabilities. Alerted amounts are gross review exposure, not confirmed loss. Associations and descriptive graph measures require independent business evidence before any conclusion about intent.

The [validation record](../VALIDATION.md) states what was executed. Peer datasets, reciprocal investigations and class role-play verdicts are outside this portfolio release.
