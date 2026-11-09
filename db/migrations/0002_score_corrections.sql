-- 0002 — score corrections (reversal events)
--
-- A reversal is a *new* score event with negative points that points at the
-- event it corrects (`corrects_event_id`). Nothing is deleted or edited.
-- This partial unique index is what makes "reverse twice" impossible:
-- one correction event per original event, enforced by the database.

CREATE UNIQUE INDEX IF NOT EXISTS ux_score_events_corrects
    ON score_events (corrects_event_id)
    WHERE corrects_event_id IS NOT NULL;
