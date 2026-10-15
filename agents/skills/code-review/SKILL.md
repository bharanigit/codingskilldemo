---
name: code-review
description: Review Databricks notebooks, PySpark code, or a pull request for correctness, security, performance, cost, and maintainability issues. Apply findings as inline notebook comments by default. Use when asked to review code, spot bugs, or check a notebook before merging.
---

# Databricks Code Review

Review the provided code following all rules in `docs.md`.

## How to review

1. Identify which technologies are present (§ 1 in `docs.md`).
2. Apply only the relevant review sections from `docs.md` — skip sections for technologies not present.
3. Use the priority order in § 2: correctness first, security second, then reliability, performance, cost, maintainability, readability, Databricks best practices.
4. Assign severity using the levels defined in § 3.
5. Report every finding in the exact table format defined in § 38.
6. Identify file, cell, and line for each finding per § 39.
7. Before reporting each finding, apply the false-positive test from § 40.
8. After all findings, write the summary from § 41 and the overall assessment from § 42.
9. Apply the review principles from § 43 throughout.

## Inline Comment Delivery (Default)

After completing the review, **always apply every finding as an inline comment** on the reviewed notebook using `createNotebookComment`. This is the default behavior — do not wait for the user to ask.

### Comment placement rules

1. **Read the notebook first** via `readAssetById` to obtain each cell's `nuid`.
2. **Anchor to code** — use `fragmentSelection` to highlight the exact code pattern the finding discusses. Only omit `fragmentSelection` when feedback is genuinely cell-wide (e.g., "monolithic cell", "split this cell").
3. **One comment per finding** — do not merge multiple findings into a single comment.
4. **Match the finding to the correct cell** — use the cell index from the findings table to locate the right `nuid`.

### Comment format

Each comment must follow this format:

```
<severity_icon> **<SEVERITY> — <Short title>**

<Explanation of why this is a problem.>

**Fix:** <Concrete recommendation with code example when applicable.>
```

Severity icons:
- 🔴 Critical / High
- 🟡 Medium
- 🔵 Low

### Example

```
🟡 **MEDIUM — Hardcoded account exclusion duplicated**

Account ID `'369844205850982'` is hardcoded here AND in Cell 12's SQL.
If the exclusion list changes, both places must be updated.

**Fix:** Extract to a constant: `EXCLUDED_ACCOUNTS = ["369844205850982"]`,
then use `~col("account_id").isin(EXCLUDED_ACCOUNTS)` in both cells.
```

### After posting comments

In the chat response, include:
- The full findings table (for reference)
- The review summary (§ 41)
- A count of how many inline comments were posted and on which cells

Do NOT skip the inline comments even if the chat response already contains the findings table. The comments are the primary deliverable — the chat summary is secondary.
