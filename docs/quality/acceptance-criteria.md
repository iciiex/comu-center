# Acceptance criteria — first PoC (DAMIISH Instagram agent)

Measurable exit criteria for roadmap Phase 1. "Works on my machine" is not one.

## Functional
1. A test Instagram user (app role) messaging the DAMIISH test account receives
   a correct answer for ≥ 90% of a fixed 30-question approved-FAQ test set,
   each answer traceable to an approved knowledge version (document id logged).
2. 100% of out-of-scope / pricing / contract / complaint test messages
   escalate to a human with **zero** automatic sends (verified in audit log).
3. Comments are out of PoC scope unless a separate criteria set is added.

## Human control (safety — all must pass, automated where possible)
4. After an operator takes over in the inbox, **zero** AI messages are sent in
   that conversation until an explicit resume — proven by an end-to-end test
   including the mid-generation takeover case.
5. Global kill-switch stops AI sending within one message cycle; attempts are
   audited (`ai_send_blocked` visible to operators).
6. Duplicate webhook deliveries (replayed ×3 in test) produce exactly one reply.

## Reliability & operations
7. Webhook endpoint: 200 in < 2 s p95 under test load; unsigned/tampered
   payloads rejected 100% (contract tests in CI).
8. Audit trail reconstructs, for any conversation: inbound, knowledge used,
   suggestion, send/block decision, takeover/resume, each with actor + time.
9. Backup taken and **restore drill passed** on the pilot environment.

## Compliance & policy
10. All test sends occur inside Meta's 24h window; no `HUMAN_AGENT` tag on
    automated messages (asserted in adapter tests).
11. No real customer accounts/messages until: App Review state documented,
    privacy policy live, DAMIISH owners sign off the approved FAQ set v1 and
    escalation policy (keywords/topics list).

## Foundation acceptance (this phase — already evidenced)
CI green (lint/types/tests/config/audit), contracts implemented + tested,
docs match code, no secrets in repo, no claim of Meta connectivity.
