"""Strict, offline Red Tiger settings-to-round association.

No network I/O, HAR loading, authentication or wagers. Callers supply already
parsed (and *locally retained*) records, then pass the selected settings to the
existing native reconcile_mode. This module does not replace settlement checks.
"""

from dataclasses import dataclass, field
from hmac import compare_digest
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


class SessionIdentityError(ValueError):
    """Missing, mismatched or ambiguous native session identity."""


@dataclass(frozen=True)
class SessionIdentity:
    table_id: str
    game_id: str
    host: str
    user_id: str
    session_id: str = field(repr=False)
    native_token: str = field(repr=False)


def _required(value: Any, name: str) -> str:
    if value is None or isinstance(value, bool) or not str(value).strip():
        raise SessionIdentityError(f"missing_or_invalid_{name}")
    return str(value)


def _host(url: str) -> str:
    parsed = urlsplit(_required(url, "url"))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SessionIdentityError("invalid_https_host")
    return parsed.hostname.lower()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SessionIdentityError(f"missing_or_invalid_{name}")
    return value


def identity_from_bootstrap(bootstrap: Mapping[str, Any]) -> SessionIdentity:
    """Read *one* config + settings pair, never a journal-global bootstrap.

    The caller normalizes native JSONL events to:
      config_response: {table_id, base_game_id, wrappedLaunchParams:{baseUrl}}
      settings_request: {url, body:{token,sessionId,playMode,gameId,...}}
      settings_response: {success,result:{user:{userId,token}}}
    """
    config = _mapping(bootstrap.get("config_response"), "config_response")
    launch = _mapping(config.get("wrappedLaunchParams"), "wrappedLaunchParams")
    settings = _mapping(bootstrap.get("settings_request"), "settings_request")
    body = _mapping(settings.get("body"), "settings_body")
    answer = _mapping(bootstrap.get("settings_response"), "settings_response")
    if body.get("playMode") != "demo" or body.get("token", object()) is not None:
        raise SessionIdentityError("settings_not_verified_demo")
    if answer.get("success") is not True:
        raise SessionIdentityError("settings_not_successful")
    if not isinstance(body.get("userData"), Mapping):
        raise SessionIdentityError("missing_user_data")
    if "custom" not in body or "listenToFrontend" not in body:
        raise SessionIdentityError("missing_settings_contract_fields")
    table_id = _required(config.get("table_id"), "table_id")
    game_id = _required(config.get("base_game_id"), "base_game_id")
    if _required(body.get("gameId"), "settings_game_id") != game_id:
        raise SessionIdentityError("config_settings_game_mismatch")
    base = _required(launch.get("baseUrl"), "base_url").rstrip("/")
    endpoint = _required(settings.get("url"), "settings_url")
    if endpoint != base + "/platform/game/settings":
        raise SessionIdentityError("settings_endpoint_mismatch")
    result = _mapping(answer.get("result"), "settings_result")
    user = _mapping(result.get("user"), "settings_user")
    return SessionIdentity(
        table_id=table_id,
        game_id=game_id,
        host=_host(base),
        user_id=_required(user.get("userId"), "native_user_id"),
        session_id=_required(body.get("sessionId"), "settings_session_id"),
        native_token=_required(user.get("token"), "native_token"),
    )


def select_bootstrap_for_round(
    *,
    table_id: str,
    financial_url: str,
    financial_body: Mapping[str, Any],
    bootstraps: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Select a unique native settings pair by strong identity.

    financial_body is a normalized request identity containing gameId,
    userId, token and, when present, sessionId. The caller must
    derive these from the actual *outgoing* round request, never from the
    bootstrap being evaluated. Balance and payout are checked separately by
    the existing reconcile_mode after selection.
    """
    requested_table = _required(table_id, "round_table_id")
    requested_host = _host(financial_url)
    req = _mapping(financial_body, "financial_body")
    requested_game = _required(req.get("gameId"), "round_game_id")
    requested_user = _required(req.get("userId"), "round_user_id")
    requested_token = _required(req.get("token"), "round_token")
    requested_session = req.get("sessionId")
    if requested_session is not None:
        requested_session = _required(requested_session, "round_session_id")
    matches = []
    for bootstrap in bootstraps:
        ident = identity_from_bootstrap(bootstrap)  # fail closed on bad evidence
        if (ident.table_id == requested_table
                and ident.game_id == requested_game
                and ident.host == requested_host
                and ident.user_id == requested_user
                and compare_digest(ident.native_token, requested_token)
                and (requested_session is None or compare_digest(ident.session_id, requested_session))):
            matches.append(bootstrap)
    if not matches:
        raise SessionIdentityError("no_matching_native_settings")
    if len(matches) != 1:
        raise SessionIdentityError("ambiguous_native_settings")
    return matches[0]
