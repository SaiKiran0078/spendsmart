# SpendSmart — Code Review and Fixes

## Issues identified and resolved

- **Placeholder repository and author links:** replaced template values in the README with the owner's GitHub profile and intended repository URL.
- **Whitespace-only account names:** registration now rejects names that become empty after trimming.
- **Bcrypt password byte limit:** registration now rejects passwords longer than bcrypt's 72-byte UTF-8 limit instead of risking a runtime hashing error or silent truncation.
- **Whitespace-only expense titles:** create/update schemas now trim titles and reject empty values.
- **CSV formula injection edge case:** CSV export now checks for formula markers after leading spaces and common control characters, not just at the first character.
- **Invalid expense date ranges:** listing expenses with `start_date` after `end_date` now returns HTTP 422 with a clear message.
- **Concurrent duplicate registrations:** database uniqueness conflicts are caught and returned as HTTP 409 instead of an unhandled server error.
- **README accuracy:** removed the inaccurate PostgreSQL-ready claim because the runtime requirements do not include a PostgreSQL driver, and removed the unimplemented roadmap section.

## Validation

- Python source compilation passed for the application and tests.
- The automated pytest suite could not be executed in this environment because dependencies are not installed and package-index network access is unavailable. Run `pip install -r requirements-dev.txt` followed by `pytest` locally or through GitHub Actions.
- Docker build and browser-level behavior have not been executed in this environment.
