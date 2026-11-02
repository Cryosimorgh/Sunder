# Codex Working Rules — Sunder

Prioritize correct implementation, short feedback cycles, and minimal token usage.

1. The local working tree is authoritative. Preserve uncommitted changes.
2. Inspect only code relevant to the task. Do not rediscover the whole architecture.
3. Use existing tests and CLI executables before creating new harnesses.
4. For physics, memory, and performance changes, use headless GPU testing by default.
5. Run one targeted failing test before editing. Record the baseline.
6. Make the smallest correct change. Fix the cause, not the symptom.
7. Run targeted correctness tests after editing. Benchmark only the affected workload.
8. Do not run full million-object campaigns, long stress tests, screenshots, or packaging unless explicitly requested or essential to the change.
9. Save complete logs to files. Return only errors, key metrics, and final results.
10. Avoid speculative refactoring, new frameworks, unnecessary abstractions, and unrelated improvements.
11. Preserve physics correctness, GPU resource safety, global fixed ticks, and staged calculation passes.
12. Never loosen correctness criteria to obtain a pass.
13. If two corrective approaches fail, reassess the root cause before making further changes.
14. Do not produce lengthy reports, architecture councils, or progress infographics for ordinary bug fixes.
15. Final response: files changed, tests passed/failed, before/after measurements, remaining blocker. Maximum 150 words.
16. Always provide exactly one ZIP handoff for each completed task so the user can pass it to the task master. Include the changed files or patch, brief reproduction commands and results, and relevant JSON/log evidence. Link that ZIP in the final response. Keep it focused; exclude build caches and unrelated historical artifacts.

Use incremental builds and reuse existing binaries and shader outputs when inputs have not changed.

Full qualification, packaging, screenshots, and infographics are reserved for gate completion or explicit requests.

The single task-master handoff ZIP is always requested and is an exception to the packaging restriction. Creating it does not authorize release builds, screenshots, full qualification or additional benchmark campaigns.

## Living architecture / gate records

Keep [docs/ENGINE_ARCHITECTURE.md](docs/ENGINE_ARCHITECTURE.md) current at **every development breakpoint**: gate close, gate reopen, release candidate, architecture-contract change, or validated performance-policy decision.

Update the relevant technical section, evidence boundary, G0–G6 status, open risks, and dated change log **in the same breakpoint commit**. Do not mark a breakpoint complete until the document is committed. Preserve rejected experiments and unverified claims. Identify local-only measurements as local evidence.

Keep the record on the working branch and carry its changes back into `main` on integration. Do not create a separate one-off report as a substitute. Ordinary small fixes do not require a full rewrite or full benchmark campaign.

Write short, precise technical English inspired by ASD-STE100, without rigid controlled-language wording.
