"""Validate a CSV dataset before using it for analysis or model training."""

import argparse
import csv
import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path


def reject_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate schema key: {key!r}.")
        obj[key] = value
    return obj


def load_rules(path):
    rules = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(rules, dict) or not rules:
        raise ValueError("The schema must be a non-empty object of column rules.")
    for name, rule in rules.items():
        if not name.strip() or not isinstance(rule, dict):
            raise ValueError("Each column must have a name and a rule object.")
        unknown = rule.keys() - {"type", "required", "unique", "allowed"}
        if unknown or rule.get("type") not in ("text", "integer", "number"):
            raise ValueError(f"Invalid rule for {name!r}.")
        for flag in ("required", "unique"):
            if flag in rule and not isinstance(rule[flag], bool):
                raise ValueError(f"{name!r}: {flag} must be true or false.")
        if "allowed" in rule:
            allowed = rule["allowed"]
            if rule["type"] != "text" or not isinstance(allowed, list):
                raise ValueError(f"{name!r}: allowed must be a list for a text column.")
            if not allowed or any(not isinstance(value, str) or not value.strip() for value in allowed):
                raise ValueError(f"{name!r}: allowed must contain non-empty strings.")
    return rules


def parse_value(value, kind):
    if kind == "text":
        return value
    if kind == "integer":
        return int(value)
    numeric_value = Decimal(value)
    if not numeric_value.is_finite():
        raise ValueError("Expected a finite number.")
    return numeric_value


def validate(path, rules):
    issues = []
    seen = {column: set() for column, rule in rules.items() if rule.get("unique")}

    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        duplicate = [column for column, count in Counter(header).items() if count > 1]
        if duplicate or set(header) != rules.keys():
            raise ValueError(
                f"CSV header mismatch. Missing: {sorted(rules.keys() - set(header))}. "
                f"Unexpected: {sorted(set(header) - rules.keys())}. Duplicate: {duplicate}."
            )

        row_count = 0
        for row_count, row in enumerate(reader, start=1):
            if len(row) != len(header):
                issues.append({"row": row_count, "column": None, "issue": "wrong_field_count"})
                continue
            for column, raw_value in zip(header, row):
                value = raw_value.strip()
                rule = rules[column]
                issue = check_value(value, rule, seen.get(column))
                if issue:
                    issues.append({"row": row_count, "column": column, "issue": issue})

    if row_count == 0:
        issues.append({"row": None, "column": None, "issue": "empty_dataset"})

    return {
        "status": "fail" if issues else "pass",
        "rows_checked": row_count,
        "issue_counts": dict(Counter(item["issue"] for item in issues)),
        "issues": issues,
    }


def check_value(value, rule, seen):
    if not value:
        return "missing" if rule.get("required") else None
    try:
        parsed = parse_value(value, rule["type"])
    except (ValueError, InvalidOperation):
        return "invalid_type"
    if "allowed" in rule and parsed not in rule["allowed"]:
        return "unknown_category"
    if seen is not None:
        if parsed in seen:
            return "duplicate"
        seen.add(parsed)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Path to a UTF-8 CSV file")
    parser.add_argument("--schema", type=Path, required=True, help="Path to the JSON column rules")
    args = parser.parse_args()

    try:
        report = validate(args.dataset, load_rules(args.schema))
    except (OSError, ValueError, csv.Error) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2))
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
