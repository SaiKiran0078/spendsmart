# SpendSmart upgrade notes — 16 November 2026

## Fixes in this package

- Expense title validation now rejects blank/whitespace-only values without silently trimming intentional whitespace.
- Expense CSV import preserves leading/trailing whitespace in title and note fields while still reversing the export-time formula-injection guard.
- CSV export continues to neutralize spreadsheet formula prefixes, including when they follow whitespace or control characters.
- The health endpoint test now verifies both application and database status fields.
- Regression coverage verifies that a leading-whitespace formula-like expense title is preserved in storage, protected on CSV export, and restored on CSV import.

## Local verification

Python source compilation and AST parsing passed during packaging. Frontend JavaScript syntax checks passed. The full pytest and Ruff suites could not be executed in the packaging environment because the required Python dependencies were unavailable and network package installation was blocked. Run `ruff check .` and `pytest -v` in the project's configured Python 3.12 virtual environment before publishing.
