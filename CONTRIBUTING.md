# Contributing

This is a portfolio project built in the open. The workflow is deliberately close
to a small team's, so the history reads like real engineering.

## Workflow

- Work on a feature branch, never directly on `main`.
- Open a pull request into `main`. Merge only when CI is green.
- Keep commits small and incremental. One logical change per commit.

## Commit convention

Conventional Commits:

```
feat:     a new user-facing feature
fix:      a bug fix
chore:    tooling, config, scaffolding
docs:     documentation only
refactor: code change that is neither a fix nor a feature
test:     adding or fixing tests
ci:       CI configuration
```

## Quality gates

- Strict TypeScript (no `any`) and typed Python (mypy or pyright).
- ESLint and Prettier for the web app; Ruff for Python.
- Tests are required and run in CI. Cover failure and edge cases.
- No secrets in the repo or the client bundle.
- No em dashes, no gradients, no fake data (see `rules.md` in the portfolio root).

## Local run

Copy `.env.example` to `.env` and fill in values. A one-command Docker Compose run
is added with the first backend milestone.
