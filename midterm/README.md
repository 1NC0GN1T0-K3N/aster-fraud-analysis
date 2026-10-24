# Midterm: rules and statistical screening

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
