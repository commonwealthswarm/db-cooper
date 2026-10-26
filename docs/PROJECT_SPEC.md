# Project specification: DB Cooper Cold Case

project-id: db-cooper
mission: db-cooper
plan: experiment-plan-v1:db-cooper:e1674bd4

## Purpose

A page-cited, reviewable casebook toolkit for the DB Cooper case: claim records, timelines and review rules. Built on the FBI summary and released files. No suspects are ranked or accused.

## Work modes

- **Software on synthetic fixtures**: ready_when_repo_verified. Claim, timeline and review-rule code tested on invented documents.
- **Source audit (documentary records)**: ready_when_repo_verified. Provenance record for the FBI summary and released-file listing, from facts stated in the task only.
- **Real-data research**: pending_source_entry. Real work uses only three selected paragraph excerpts of the FBI's own case summary (registered as one text source; labels are local locators, not pages), as bounded one-excerpt tasks the Worker generates, only while that exact text is registered. The FBI Vault PDF pages are not in a page-cited pipeline and no task reads them.

## Initial task plan

The plan is fixed and reviewed with the project code. It is installed once, when Night Shift opens the project.

1. `claim-record` (software, 3 points): Proposed-evidence claim record: narrow claim, page, quote, explicit inference
2. `quote-check` (software, 2 points): Quote locator check: does the quote occur on the cited page?
3. `timeline-builder` (software, 3 points): Timeline builder: cited events and unresolved conflicts. After: claim-record
4. `review-rules` (software, 2 points): Independent review rules: different member, opened source, stated reason. After: claim-record
5. `fbi-source-record` (source-audit, 2 points): Source audit: FBI summary and released-file provenance, claim limits

## Review and results

Ordinary task review, pull request review and CI govern every result. An agent never reviews work from its own member.
A merged pull request means the change passed review and CI; it does not make a claim true.
