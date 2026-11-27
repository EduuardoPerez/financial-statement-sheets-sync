# Repository coordination map

| Repository | Responsibility | State |
| --- | --- | --- |
| [financial-statement-processor](https://github.com/EduuardoPerez/financial-statement-processor) | Parse source statements and produce versioned observations and coverage. | Existing |
| [financial-statement-sheets-sync](https://github.com/EduuardoPerez/financial-statement-sheets-sync) | Reconcile observations, retain review decisions, and prepare reviewed imports. | Existing |
| financial-statement-orchestrator | Sequence local commands and resume runs without duplicating accounting rules. | Planned |

The processor owns the [v1.0 input contract](https://github.com/EduuardoPerez/financial-statement-processor/blob/0f838cb6be1ecf8650d64b10a6d33fccbbc9d43b/docs/RECONCILIATION_DATA_CONTRACT_V1.md).
When work depends on that contract, look for a local processor checkout beside
this repository or in the contributor's configured workspace. Confirm its Git
remote and working-tree state, then read its current contract, exporter, and
relevant tests. If no checkout is available, use the processor's GitHub
repository. Verify the consumer with synthetic examples and actual processor
output when available.
The synchronizer's future command and result interface will be the
orchestrator boundary. Google Sheets writes require a reviewed preview and
separate authorization. The [Project](https://github.com/users/EduuardoPerez/projects/1)
owns task state; repository docs describe stable responsibilities only.
