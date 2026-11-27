# Financial statement Sheets sync

A local Python component for reconciliation and reviewed Google Sheets import
preparation. This repository currently contains the development scaffold and
task context; reconciliation and Sheets writes are not implemented.

## Setup

Install [uv](https://docs.astral.sh/uv/), then run:

```sh
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

Python 3.15 is selected by `.python-version`. The input is the processor's
[reconciliation package v1](https://github.com/EduuardoPerez/financial-statement-processor/blob/0f838cb6be1ecf8650d64b10a6d33fccbbc9d43b/docs/RECONCILIATION_DATA_CONTRACT_V1.md).
See [project context](docs/CONTEXT.md) for ownership, current work, and evidence
limits.

## Shared agent skills

Install the [agent-skills package](https://github.com/EduuardoPerez/agent-skills#install-in-codex).
This repository configures the Project Kanban and multi-repository coordination
skills under `.agents/skills-config/agent-skills/`; the processor's local parser
skills remain in the processor repository. Audit each profile with the package's
`scripts/audit_profile.py` before changing profile keys. Check the package's
README for current installation and update commands.
