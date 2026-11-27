# Repository guidelines

## Language and privacy

Write project-authored content in English. Use only synthetic examples in Git.
Never commit statements, real financial values, transaction identifiers,
private spreadsheet links, credentials, local paths, or generated reports.
Keep local inputs, outputs, and private evidence outside version control.

## Responsibility

This repository consumes the processor's versioned reconciliation package,
normalizes observations, proposes evidence-backed links, persists review
decisions, and prepares reviewed Google Sheets imports. It does not parse bank
statements or orchestrate the full workflow. Source observations, reconciliation
links, purchases, installment charges, and import rows have distinct identities.
Never infer a purchase or an absent counterpart from date and amount alone.
Do not write to a real sheet without a reviewed preview and explicit approval.

## Development

Use Python 3.15, uv, a src package, pytest, Ruff, and mypy. Run `uv sync`,
`uv run pytest`, `uv run ruff check src tests`,
`uv run ruff format --check src tests`, and `uv run mypy src`.
Keep changes focused; inspect Git status and applicable contracts before work.
Use the Project cards linked in [docs/CONTEXT.md](docs/CONTEXT.md) for scope and
handoffs. Do not commit, push, or open pull requests unless requested.
