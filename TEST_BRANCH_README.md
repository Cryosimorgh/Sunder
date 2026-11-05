# Sunder test branch

This branch preserves the pre-cleanup test and diagnostic tools from `main` at commit `8c50d6db83a1c31ad6fac7d52dc97c59b05a298b`.

Store all newly created standalone test files and experimental diagnostics here, not on `main`. Test an implementation change by merging/cherry-picking the relevant production commit into this branch, or by using a separate worktree with the proposed source files. Do not merge test-only files back into the production branch.

Existing build and native verification dependencies have not yet been separated from production source. Until they are, keep the tests and build pipeline operational rather than deleting required source files on `main`.
