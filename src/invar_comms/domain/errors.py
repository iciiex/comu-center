"""Domain errors. Every guard in the core raises one of these — never silent failure."""


class DomainError(Exception):
    """Base class for all domain errors."""


class ValidationError(DomainError, ValueError):
    """Input violates a contract (message, knowledge, configuration, webhook payload)."""


class AuthorizationError(DomainError, PermissionError):
    """Actor is not permitted to perform the requested action in this product scope."""


class InvalidStateTransition(DomainError):
    """Conversation-control state machine rejected the requested transition."""


class AISendBlocked(DomainError):
    """AI sending is blocked (human control, kill-switch, or stale control version).

    This is a server-side guard. It cannot be overridden by prompt content,
    message content, or retrieved documents (all untrusted input).
    """


class LiveSendDisabled(DomainError):
    """Live sending to an external platform is not enabled / not implemented."""


class ConcurrencyConflict(DomainError):
    """Optimistic-concurrency check failed (stored control_version changed).

    Raised by repositories on compare-and-swap saves: another writer changed
    the conversation control state first, so this write must be discarded
    and re-evaluated — never silently overwritten.
    """
