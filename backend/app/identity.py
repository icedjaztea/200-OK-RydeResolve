"""Demo identity mapping — credentials to stable individuals.

This module maps demo passcodes to stable individual demo identities
on the server.  The browser never supplies an identity; it only sends
the X-Demo-Key header, and the server resolves who the caller is.

Identities:
    Rider A  (rider_a)   — alias for DEMO_RIDER_KEY
    Rider B  (rider_b)   — DEMO_RIDER_B_KEY
    Driver A (driver_a)  — alias for DEMO_DRIVER_KEY
    Driver B (driver_b)  — DEMO_DRIVER_B_KEY
    Reviewer (reviewer)  — DEMO_REVIEWER_KEY

Extra keys may be supplied through environment variables or Secret
Manager (via the setting() helper).  No secrets are hardcoded.

These are DEMO identities only — they do not provide production-grade
account authentication.
"""
from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Optional

from .config import setting


@dataclass(frozen=True)
class DemoIdentity:
    """A resolved demo identity."""
    role: str          # 'rider' | 'driver' | 'reviewer'
    identity_id: str   # 'rider_a' | 'rider_b' | 'driver_a' | 'driver_b' | 'reviewer'


# ---------------------------------------------------------------------------
# Credential → identity registry.
#
# Each entry maps an environment variable name to (role, identity_id).
# The existing DEMO_RIDER_KEY / DEMO_DRIVER_KEY remain as aliases for the
# "A" identity, preserving backward compatibility with deployed configs.
# ---------------------------------------------------------------------------
_CREDENTIAL_MAP = [
    ('DEMO_RIDER_KEY',    'rider',    'rider_a'),
    ('DEMO_RIDER_B_KEY',  'rider',    'rider_b'),
    ('DEMO_DRIVER_KEY',   'driver',   'driver_a'),
    ('DEMO_DRIVER_B_KEY', 'driver',   'driver_b'),
    ('DEMO_REVIEWER_KEY', 'reviewer', 'reviewer'),
]

# Default placeholder values that must be replaced before hosted deployment.
_DEFAULT_PLACEHOLDERS = {'rider': 'change-rider-key', 'driver': 'change-driver-key', 'reviewer': 'change-reviewer-key'}


def _resolve_identity(x_demo_key: Optional[str]) -> Optional[DemoIdentity]:
    """Resolve an X-Demo-Key to a DemoIdentity, or None if no match.

    Uses constant-time comparison to prevent timing attacks (best effort
    for demo; not a production auth layer).
    """
    if not x_demo_key:
        return None

    for env_var, role, identity_id in _CREDENTIAL_MAP:
        expected = setting(env_var, '')
        # Skip unset keys — they should not match anything.
        if not expected:
            continue
        # Skip placeholder defaults when in hosted/firestore mode.
        if setting('APP_MODE', 'memory') == 'firestore' and expected == _DEFAULT_PLACEHOLDERS.get(role, ''):
            continue
        if hmac.compare_digest(x_demo_key, expected):
            return DemoIdentity(role=role, identity_id=identity_id)

    return None


def authenticate(x_demo_key: Optional[str]) -> DemoIdentity:
    """Authenticate and return a DemoIdentity.

    Raises ValueError if the key is invalid or missing.
    The caller (FastAPI dependency) converts this to an HTTP 401.
    """
    identity = _resolve_identity(x_demo_key)
    if identity is None:
        raise ValueError('Invalid synthetic-demo key')
    return identity


def is_reviewer(identity: DemoIdentity) -> bool:
    return identity.role == 'reviewer'


def is_party(identity: DemoIdentity) -> bool:
    """A party is a rider or driver (not reviewer)."""
    return identity.role in ('rider', 'driver')


# ---------------------------------------------------------------------------
# Deterministic seeded-case identity mapping.
#
# Existing synthetic fixture cases are assigned to specific demo
# identities so that Rider A sees a different set than Rider B.
# This mapping is hardcoded (not env-var driven) because the fixture
# case IDs are themselves synthetic constants.
#
# Rider-filed cases → assigned to rider_a unless explicitly mapped to rider_b.
# Driver-filed cases → assigned to driver_a unless explicitly mapped to driver_b.
# The counterparty on each case is also assigned so drivers can see
# cases where they are the respondent.
# ---------------------------------------------------------------------------

# (case_id → (rider_id, driver_id))
# rider_id / driver_id may be None when that party is not involved.
#
# Cases that existing tests reply to as RIDER must be owned by rider_a.
# Cases that existing tests reply to as DRIVER must be owned by driver_a.
# A few cases are assigned to rider_b / driver_b for isolation testing.
_SEED_CASE_OWNERS: dict[str, tuple[str | None, str | None]] = {
    # Rider A cases (rider files the dispute, driver_a or driver_b is counterparty)
    'DEMO-FARE-50':         ('rider_a', 'driver_a'),
    'DEMO-FARE-CLARIFY':    ('rider_a', 'driver_a'),   # test replies as RIDER
    'DEMO-FARE-CONFLICT':   ('rider_a', 'driver_a'),
    'DEMO-FARE-OVER50':     ('rider_a', 'driver_b'),
    'DEMO-NOSHOW-VALID':    ('rider_a', 'driver_a'),
    'DEMO-NOSHOW-VOID':     ('rider_a', 'driver_a'),   # test replies as DRIVER
    'DEMO-ROUTE-SHORT':     ('rider_a', 'driver_b'),
    'DEMO-SAFETY-IN-FARE':  ('rider_a', 'driver_a'),
    'DISP-001':             ('rider_a', 'driver_a'),
    'DISP-002':             ('rider_a', 'driver_b'),
    'DISP-003':             ('rider_a', 'driver_a'),
    # Rider B case for isolation testing
    'DEMO-DAMAGE-DISPUTED': ('rider_b', 'driver_b'),   # driver-filed, rider_b respondent
}


def seed_case_owners(case_id: str, filed_by: str) -> tuple[str | None, str | None]:
    """Return (rider_id, driver_id) for a seeded fixture case.

    Falls back to ('rider_a', 'driver_a') for any unmapped fixture —
    this is safe because all known fixtures are in _SEED_CASE_OWNERS.
    """
    if case_id in _SEED_CASE_OWNERS:
        return _SEED_CASE_OWNERS[case_id]
    # Defensive default for any future fixture not yet mapped.
    if filed_by == 'driver':
        return (None, 'driver_a')
    return ('rider_a', None)
