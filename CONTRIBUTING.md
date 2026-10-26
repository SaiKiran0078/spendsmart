# Contributing to SpendSmart

Thanks for your interest! Contributions of all sizes are welcome.

1. Fork the repo and create a branch: `git checkout -b feature/my-change`
2. Install dev dependencies: `make install`
3. Make your change and add or update tests in `tests/`
4. Run `make lint` and `make test` — both must pass
5. Commit using clear messages (e.g. `feat: add recurring expenses`)
6. Open a pull request using the template

## Code style
- Formatting and linting are handled by [Ruff](https://docs.astral.sh/ruff/)
- Keep routers thin; put reusable logic in helpers
- Every new endpoint needs at least one test
