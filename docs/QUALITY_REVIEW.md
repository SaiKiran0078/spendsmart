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

---

## v2 upgrade notes

- **Preserved:** strict `SECRET_KEY` validation, trimmed/blank-string validators, bcrypt byte limit, date-range validation, duplicate-registration handling and the hardened CSV formula guard.
- **Added:** income, category budgets, goals, recurring bills, analytics/insights, CSV import, account management, login rate limiting, security headers and a new multi-page UI.
- **Compatibility:** no existing table or endpoint contract was changed; new fields on the summary response are additive.
- **Hardening:** the UI never uses `innerHTML` for data; CSP restricts scripts to this origin and the pinned Chart.js CDN build.

### Validation status

- Python and JavaScript sources compile / pass `node --check`; the pure date logic was executed directly.
- The full pytest suite and Docker build could not be run in the authoring environment (no package-index access). Run `pip install -r requirements-dev.txt && pytest` locally or let GitHub Actions run it, and fix anything it reports.
- The UI has not been exercised in a browser by the author of this upgrade; run `make seed && make run` and click through each page.



## Upgrade hardening pass (2026-11-16)

- **API cache controls:** API responses now include `Cache-Control: no-store` so authenticated finance data is not stored by intermediary/browser caches.
- **Database readiness:** `/api/health` checks the database with `SELECT 1` and returns HTTP 503 when the database cannot be reached.
- **SQLite integrity:** SQLite connections enable foreign-key enforcement so declared ownership cascades are honored consistently.
- **JWT configuration:** explicitly limits the configured signing algorithm to the supported HS256 implementation.
- **Monetary validation:** all writable amount fields reject NaN and infinity in addition to enforcing their existing numeric bounds.
- **Analytics request validation:** summary and trend endpoints reject partial year/month filters instead of silently combining a supplied year with the current month (or vice versa).
- **Historical budget status:** setting a category limit accepts optional year/month parameters so the returned status can reflect the selected month.
- **Frontend resilience:** API fetches now have a 30-second timeout and distinguish timeout feedback from connection errors.
- **Month navigation:** the dashboard month switcher cannot navigate into future months.
- **Downloads:** CSV export object URLs are revoked after the browser has had time to start the download.
- **CI coverage:** added Python compilation and JavaScript syntax checks to the v2 CI workflow.
- **Build hygiene:** Docker dependency installation upgrades pip before installing the pinned runtime requirements.

### Validation performed for this pass

- All 36 Python source files compile.
- All 16 frontend JavaScript modules pass Node.js syntax checks.
- Pure recurring-date checks pass for leap-month clamping, restoration of a 31st-day anchor, and leap-year annual recurrence.
- Full pytest and Ruff could not run in this execution environment because `bcrypt` and Ruff are not preinstalled and package-index access is unavailable. Docker build and browser E2E checks remain to be run by CI / a local Docker-enabled environment.
