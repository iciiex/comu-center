import hashlib
import hmac

import pytest

from invar_comms.adapters.meta_instagram import (
    MetaInstagramAdapter,
    verify_payload_signature,
    verify_webhook_subscription,
)
from invar_comms.config import load_settings
from invar_comms.domain.errors import LiveSendDisabled, ValidationError


def test_defaults_are_fail_closed() -> None:
    s = load_settings({})
    assert s.ai_send_enabled is False
    assert s.meta_live_send_enabled is False
    assert s.enabled_products == frozenset({"damiish"})


def test_live_meta_without_credentials_is_startup_error() -> None:
    with pytest.raises(ValidationError):
        load_settings({"INVAR_AI_SEND_ENABLED": "true",
                       "INVAR_META_LIVE_SEND_ENABLED": "true"})


def test_secrets_redacted_in_summary_and_repr() -> None:
    s = load_settings({"INVAR_META_APP_SECRET": "super-secret-value"})
    assert "super-secret-value" not in s.redacted_summary()
    assert "super-secret-value" not in repr(s)
    assert "meta_app_secret: set" in s.redacted_summary()


def test_webhook_subscription_handshake() -> None:
    assert verify_webhook_subscription(
        mode="subscribe", verify_token="tok", challenge="12345", expected_token="tok"
    ) == "12345"
    with pytest.raises(ValidationError):
        verify_webhook_subscription(
            mode="subscribe", verify_token="wrong", challenge="1", expected_token="tok")


def test_payload_signature_verification_over_raw_body() -> None:
    body = b'{"object":"instagram","entry":[]}'
    secret = "app-secret-test-only"  # noqa: S105 — test fixture, not a real credential
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    verify_payload_signature(raw_body=body, signature_header=sig, app_secret=secret)
    with pytest.raises(ValidationError):
        verify_payload_signature(raw_body=b"tampered", signature_header=sig,
                                 app_secret=secret)
    with pytest.raises(ValidationError):
        verify_payload_signature(raw_body=body, signature_header=None, app_secret=secret)
    with pytest.raises(ValidationError):
        verify_payload_signature(raw_body=body, signature_header=sig, app_secret="")


def test_meta_adapter_never_fakes_live_sending() -> None:
    adapter = MetaInstagramAdapter()
    with pytest.raises(LiveSendDisabled):
        adapter.send_text(conversation_id="c", external_contact_id="u", text="hi")
    with pytest.raises(ValidationError):
        adapter.normalize_inbound({"object": "unknown"})
