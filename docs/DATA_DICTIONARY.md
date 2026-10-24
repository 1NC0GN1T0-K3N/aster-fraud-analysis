# Data dictionary — Fraud Analytics

All values are synthetic. Amounts are THB. Invalid records are intentional test cases and are preserved in quarantine. Midterm and final schemas differ and should not be joined as one ledger.

## Midterm source tables

| CSV | Fields and interpretation |
|---|---|
| `employees.csv` | `emp_id` employee key; `emp_name` fictional name; `department`, `role`; `bank_account`, `address` fictional linkage evidence; `approval_limit_thb` approval limit; `active_flag` activity marker |
| `merchants.csv` | `vendor_id` merchant key; `vendor_name`; `category` expense category; `owner_name`, `bank_account`, `address` fictional relationship evidence; `registration_date`; `risk_country`; `active_flag` |
| `expense_claims.csv` | `invoice_id` claim key; `invoice_number` merchant receipt; `vendor_id` merchant reference; `employee_id` submitter; `approver_id`; `invoice_date` claim date; `amount_thb`; `description`; `po_id` trip reference; `payment_method`; `currency` |

The retained accounting column names refer to employee reimbursements. Policy caps are classroom assumptions defined in `midterm/case_config.json`. Seven invalid claim rows and one invalid record in each master table are quarantined. Multiple alerts can refer to one claim; review exposure must deduplicate claim IDs.

## Final source tables

| CSV | Fields and interpretation |
|---|---|
| `employees.csv` | `employee_id` key; `employee_name`; `department`; `supervisor_id` usual approver; `bank_account` fictional employee account; `active` marker |
| `merchants.csv` | `merchant_id` key; `merchant_name`; `bank_account` fictional receiving account; `registered_date`; `disclosed_employee_link` marks an already disclosed legitimate relationship |
| `trips.csv` | `trip_id` key; `employee_id`; `city`; `approved_nights`; `start_date`; `approved` indicator |
| `approvals.csv` | `approval_id` key; `approver_id`; `approved_at`; `exception_approved`; `exception_reference`; `approved_allowance_thb` total allowance including authorized exceptions |
| `expense_claims.csv` | `claim_id` key; `employee_id`, `merchant_id`, `approver_id`, `trip_id`, `approval_id` references; `receipt_number`; `category`; `city`; `nights`; `amount_thb`; `submitted_at`; `currency`; `business_purpose` |

IDs establish joins and provenance; employee, merchant and claim IDs do not enter classifier predictors. The per-night hotel allowance is THB 9,000 before authorized exceptions. Other category caps and fictional city benchmarks are defined in `final/tools/project_core.py`.

## Final model predictors

| Predictor | Meaning |
|---|---|
| `amount_to_allowance` | Claim amount / approved allowance |
| `market_rate_ratio` | Hotel amount / (fictional city rate × claimed nights); other categories use their policy cap |
| `approval_minutes` | Minutes from submission to approval |
| `submission_lag_days` | Calendar days from trip start to submission |
| `merchant_age_days` | Days from merchant registration to submission, floored at zero |
| `claims_prior_30d` | Earlier employee claims in the trailing 30 days |
| `merchant_share_prior_90d` | Share of earlier employee claims using this merchant in the trailing 90 days |
| `receipt_seen_before` | Whether the same merchant/receipt pair appeared earlier |
| `self_approved` | Employee and approver are the same |
| `bank_match` | Employee and merchant synthetic accounts match |
| `exception_approved` | Recorded approved exception |
| `trip_consistent` | Employee/city match the trip and claimed nights do not exceed approved nights |
| `usual_approver` | Approver matches the employee's supervisor |
| `category`, `department` | One-hot-encoded categorical inputs |

For hotel `market_rate_ratio`, the denominator is `(city benchmark × nights)`. Prior-history features follow submitted timestamp and claim-ID order. The scoring point is after approval and before reimbursement.

## Evaluation and outputs

Generated `private/ground_truth.csv` holds the planted `is_fraud` label, `scheme`, case grouping and synthetic excess payments. It is used to evaluate model errors, not as classifier input. `models/` and `private/` are created by the code and ignored by Git.

`rule_alert`, `lr_alert`, `rf_alert` and `selected_alert` are binary review indicators. The corresponding `*_score` fields are uncalibrated ranking outputs. `split` identifies training, validation, test or later-period records. `tp`, `fp`, `fn`, `tn` are confusion counts; average precision summarizes ranked precision–recall performance.

Graph links record observed expense affiliation with source claim IDs, counts and amounts. They do not establish ownership, direct employee relationships or payment flow. Disclosed legitimate relationships are retained to demonstrate this distinction.
