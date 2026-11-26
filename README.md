# Dataset Check

A Python command-line tool that checks a CSV file against explicit column rules before it enters an analysis or model-training workflow. It reports where a row failed and why. The included example uses fictional retail orders.

## Run the examples

Use Python 3.10 or later. The tool uses the Python standard library.

```sh
python dataset_check.py examples/orders_valid.csv --schema examples/schema.json
python dataset_check.py examples/orders_invalid.csv --schema examples/schema.json
python -m unittest -v
```

The clean sample passes with three rows.The second sample reports six issues across five rows, including a duplicated order ID, a missing quantity, and an unknown sales channel.

```json
{"row": 2, "column": "order_id", "issue": "duplicate"}
```

Row numbers start at 1 for the first record after the header. The report omits raw cell values. Exit code `0` indicates a pass, `1` indicates data issues, and `2` indicates an input error such as mismatched headers or invalid rules.

## Use a different dataset

Create a JSON file with a rule for each column. The header must contain the same column names in any order. The supported types are `text`, `integer`, and `number`. Use `required` for non-empty cells, `unique` for unique valid values, and `allowed` to restrict text values to a set. The tool trims whitespace before validating a cell and treats blank optional cells as missing.

```json
{
  "order_id": {"type": "integer", "required": true, "unique": true},
  "channel": {"type": "text", "required": true, "allowed": ["web", "store"]}
}
```

The project targets samll batch datasets. It retains unique values and row issues in memory for the duration of the run. Domain rules such as a minimum acceptable quantity can be added as a follow-up with a corresponding sample and test.
