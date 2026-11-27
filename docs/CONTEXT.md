# Synchronizer context

The synchronizer consumes the processor's [v1.0 JSONL and manifest contract](https://github.com/EduuardoPerez/financial-statement-processor/blob/0f838cb6be1ecf8650d64b10a6d33fccbbc9d43b/docs/RECONCILIATION_DATA_CONTRACT_V1.md). It validates the manifest digest, count,
version, and coverage before interpreting observations. The producer owns the
contract. Consumer compatibility must be tested with synthetic examples and
an actual processor export. Source rows remain observations; candidate links,
purchase identities, installment charges, and future sheet import rows are
separate.

The [Project](https://github.com/users/EduuardoPerez/projects/1) tracks current
status. Synchronizer [#1](https://github.com/EduuardoPerez/financial-statement-sheets-sync/issues/1)
reads the package; [#2](https://github.com/EduuardoPerez/financial-statement-sheets-sync/issues/2)
groups Mercado Pago operations; [#3](https://github.com/EduuardoPerez/financial-statement-sheets-sync/issues/3)
finds bank candidates; and [#4](https://github.com/EduuardoPerez/financial-statement-sheets-sync/issues/4)
produces reproducible links and review output. Processor [#18](https://github.com/EduuardoPerez/financial-statement-processor/issues/18)
tracks persistent human review; processor [#16–#19](https://github.com/EduuardoPerez/financial-statement-processor/issues/16)
cover read-only sheet inspection through test-copy validation. The separate
[orchestrator repository card](https://github.com/EduuardoPerez/financial-statement-sheets-sync/issues/5)
waits for the synchronizer command/result boundary.

Prior private research found 253 transaction CSV to balance links and 51 paired
balance inflow/payment groups. Those are candidate evidence, not confirmed
purchases. Discounted payments, refunds, adjustments, and conflicting signs
need separate review. The processor's `DUPLICATED:` Excel marker compares date
and absolute amount only; it neither removes rows nor proves identity.
The updated private v1 package includes 1,329 observations, but four expected
statements are missing, several export ranges are unverified, and complete
Activity coverage is unavailable. Missing counterparts therefore remain pending.
No private statements, package, spreadsheet links, or detailed evidence live
in this repository.
