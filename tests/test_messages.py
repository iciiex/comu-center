import pytest
from helpers import make_message

from invar_comms.domain.errors import ValidationError
from invar_comms.domain.messages import MessageDeduplicator


def test_valid_message_and_scoped_contact() -> None:
    msg = make_message()
    assert msg.contact.scoped_key == "instagram:ig-acct-1:ig-user-42"


def test_contact_ids_are_not_globally_unique_idempotency_is_account_scoped() -> None:
    a = make_message(external_event_id="evt-9", channel_account_id="acct-A")
    b = make_message(external_event_id="evt-9", channel_account_id="acct-B")
    assert a.idempotency_key != b.idempotency_key


def test_idempotency_key_stable_for_redelivery() -> None:
    assert make_message().idempotency_key == make_message().idempotency_key


def test_deduplicator_seen_exactly_once() -> None:
    dedupe = MessageDeduplicator()
    assert dedupe.seen(make_message()) is False
    assert dedupe.seen(make_message()) is True


def test_rejects_naive_timestamp() -> None:
    from datetime import datetime

    with pytest.raises(ValidationError):
        make_message(occurred_at=datetime(2026, 10, 22, 10, 0))  # noqa: DTZ001 naive on purpose


def test_rejects_empty_text_message() -> None:
    with pytest.raises(ValidationError):
        make_message(text="  ")


def test_rejects_bad_product_slug_and_schema_version() -> None:
    with pytest.raises(ValidationError):
        make_message(product_id="DAMIISH!")
    with pytest.raises(ValidationError):
        make_message(schema_version=99)
