# Midterm — rules and statistical screening

A synthetic travel-expense ledger with 176 raw claims, 169 valid claims and seven quarantined claim rows. Two invalid master records are also quarantined. The original offline analysis reported 42 alert rows and THB 285,800 gross review exposure across 18 unique claims. Review exposure is not confirmed loss.

## Run offline

With Node.js 22 or newer, from this folder:

```sh
node --test tools/pipeline.test.mjs
node tools/run_analysis.mjs
```

The runner uses the analytics code from the active deterministic workflow and writes `notebook_run/findings.json`. No external packages, accounts or network calls are needed.

## Optional n8n workflow

Import either workflow JSON into n8n. Configure your own PostgreSQL connection for each database node. Use a disposable classroom database: the setup node resets the case schema. Run setup, upload each of the three CSV files, then run controls and analytics. Accounting names map `invoice_id` to claim ID, `invoice_number` to receipt number, `vendor_id` to merchant ID, and `po_id` to trip reference.

The Gemini variant adds an optional narrative review after deterministic calculations; configure your own Gemini credentials. It masks account values and checks structured responses, but narrative output still needs human review. Live n8n/PostgreSQL/Gemini execution has not been verified for this public export.

Methods include account linkage, receipt reuse, self-approval, policy caps, robust z-scores, Welch peer comparisons and an exploratory breakpoint scan. Repeated observations and scan-selected windows limit inference. All identities, accounts and transactions are fictional.

## Files and saved evidence

- `data/`: the employee, merchant and claim CSVs used by both execution routes.
- `case_config.json`: field mappings, target/category settings and fictional policy caps.
- `tools/pipeline_core.mjs`: shared integrity, screening and statistical functions.
- `tools/run_analysis.mjs`: offline execution of the deterministic workflow analytics.
- `tools/pipeline.test.mjs`: 12 original tests covering quarantine, reconciliation, rules and statistical edge cases.
- `results/findings.json`: committed control totals, profiles, statistical comparisons, alerts and interpretation.

The [data dictionary](../docs/DATA_DICTIONARY.md) explains all three schemas. No npm installation is required. The included `package.json` also exposes `npm test` and `npm run analyze` when run from this directory.

Do not upload real personnel or bank records as part of this demonstration. The configured database schema is reset by setup. Keep workflow form endpoints local or configure access controls before exposing them. PostgreSQL and Gemini credentials are configured inside your own n8n instance and are not part of these exports.

## Interpreting findings

An alert row is a triggered check, not a unique fraud event. The 42 alerts overlap across 18 unique claims. THB 285,800 is the gross amount requiring review, not a measured loss. Account matches, reused receipts and policy breaches still require supporting documents and legitimate-exception checks. Statistical comparisons are exploratory because the window is selected from the same observations and repeated claims may be correlated.

The live n8n path and optional AI narration are separate integration steps. Passing offline tests does not verify your database connection, import compatibility or model credentials.
