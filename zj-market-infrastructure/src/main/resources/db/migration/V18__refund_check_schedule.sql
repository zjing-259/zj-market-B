-- V17 was already applied during acceptance; preserve its checksum.
ALTER TABLE b_refund_task ADD check_previous_due_ms BIGINT;
UPDATE b_refund_task SET check_previous_due_ms=next_attempt_ms WHERE check_only=TRUE;
