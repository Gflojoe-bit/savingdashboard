# Sample data for the importer

## `plaid_transactions_raw.csv`

388 rows, 28 columns. One row per transaction from a Plaid sandbox pull
(institution `ins_109508` "First Platypus Bank") spanning roughly two years.

Columns mirror Plaid's `/transactions/get` JSON 1:1 — top-level scalars are
direct columns, nested objects (`personal_finance_category`, `location`,
`payment_meta`, `counterparties`) are stored as JSON strings in their cells
so nothing is lost.

**Sign convention is Plaid-native:** positive `amount` = debit/spending,
negative `amount` = credit/refund/deposit. This is the **opposite** of our
internal `Transaction.amount` convention (positive = income). The importer
is the right place to flip the sign — see `docs/plaid-data-shape.md` for
the full mapping table.

Regenerate with `scripts/plaid_raw_csv.py` (requires the JSON dump from
`scripts/plaid_explore.py`, which needs Plaid sandbox credentials in `.env`).
