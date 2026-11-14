"""Validate a Belatra demo HAR offline, without network, replay or session disclosure."""
from __future__ import annotations

import argparse
import base64
import binascii
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import parse_qs, urljoin, urlsplit

HOST = "demo.bltrm.com"
LAUNCH_PATH = "/belatra/demo"
MAX_CLOCK_DRIFT_SECONDS = 300
SAFE_GAME = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class BelatraContractError(ValueError):
    """Stable diagnostic that does not include session values."""


def _fail(reason: str) -> None:
    raise BelatraContractError(reason)


def _url(value: Any):
    if not isinstance(value, str):
        _fail("invalid_url")
    result = urlsplit(value)
    if (result.scheme != "https" or result.hostname != HOST
            or result.username or result.password or result.port not in (None, 443)):
        _fail("untrusted_demo_host")
    return result


def _header(headers: Any, name: str) -> str:
    values = [h.get("value") for h in headers or []
              if isinstance(h, Mapping) and str(h.get("name", "")).lower() == name.lower()]
    if len(values) != 1 or not isinstance(values[0], str):
        _fail("missing_or_duplicate_" + name.lower().replace("-", "_"))
    return values[0]


def _one(query: str, key: str) -> str:
    data = parse_qs(query, keep_blank_values=True, strict_parsing=True)
    values = data.get(key, [])
    if len(values) != 1 or not values[0]:
        _fail("missing_or_duplicate_" + key)
    return values[0]


def _request(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    request = entry.get("request")
    if not isinstance(request, Mapping):
        _fail("missing_request")
    return request


def _response(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    response = entry.get("response")
    if not isinstance(response, Mapping):
        _fail("missing_response")
    return response


def _entry_time(entry: Mapping[str, Any]) -> float:
    stamp = entry.get("startedDateTime")
    if not isinstance(stamp, str):
        _fail("missing_event_time")
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        _fail("invalid_event_time")


def _packet(encoded: Any, event_time: float) -> int:
    if not isinstance(encoded, str) or not encoded or len(encoded) > 20_000_000:
        _fail("invalid_packet")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        _fail("packet_not_base64")
    if len(raw) < 8:
        _fail("packet_header_missing")
    # Observed binary framing: bytes 4..7 contain little-endian Unix seconds.
    epoch = int.from_bytes(raw[4:8], "little")
    if abs(epoch - event_time) > MAX_CLOCK_DRIFT_SECONDS:
        _fail("packet_epoch_mismatch")
    return len(raw)


def _one_entry(entries: list[Mapping[str, Any]], method: str, path: str) -> Mapping[str, Any]:
    matches = [e for e in entries if _request(e).get("method") == method
               and _url(_request(e).get("url")).path == path]
    if len(matches) != 1:
        _fail("missing_or_duplicate_" + path.strip("/").replace("/", "_") + "_step")
    return matches[0]


def analyze_har(har: Mapping[str, Any]) -> dict[str, Any]:
    """Only publish non-secret metadata, never URLs, cookies, payloads or IDs."""
    log = har.get("log")
    if not isinstance(log, Mapping) or not isinstance(log.get("entries"), list):
        _fail("invalid_har_entries")
    entries = []
    for entry in log["entries"]:
        if not isinstance(entry, Mapping):
            _fail("invalid_har_entry")
        req = _request(entry)
        parsed = urlsplit(str(req.get("url", "")))
        if parsed.hostname == HOST:
            _url(req.get("url"))
            entries.append(entry)

    launch = _one_entry(entries, "GET", LAUNCH_PATH)
    launch_req = _request(launch)
    launch_res = _response(launch)
    if launch_res.get("status") not in (301, 302, 303, 307, 308):
        _fail("launcher_redirect_not_observed")
    query = _url(launch_req["url"]).query
    game = _one(query, "game")
    language = _one(query, "language")
    if not SAFE_GAME.fullmatch(game) or not re.fullmatch(r"[A-Za-z]{2}(?:-[A-Za-z]{2})?", language):
        _fail("invalid_catalog_identity")
    location = urljoin(launch_req["url"], _header(launch_res.get("headers"), "location"))
    redirected = _url(location)
    if redirected.path != "/":
        _fail("unexpected_launch_redirect_path")
    sid = _one(redirected.query, "sid")
    modification = _one(redirected.query, "modification")
    root = _one_entry(entries, "GET", "/")
    root_query = _url(_request(root)["url"]).query
    if (_one(root_query, "sid"), _one(root_query, "modification")) != (sid, modification):
        _fail("redirect_session_changed")
    if _response(root).get("status") != 200:
        _fail("game_document_not_200")

    datalist = _one_entry(entries, "POST", "/user/datalist")
    if _response(datalist).get("status") != 200:
        _fail("datalist_not_200")
    try:
        body = json.loads(_request(datalist)["postData"]["text"])
    except (KeyError, TypeError, ValueError):
        _fail("invalid_datalist_request")
    if not isinstance(body, dict) or body.get("sid") != sid or not isinstance(body.get("datatype"), str):
        _fail("datalist_session_mismatch")

    rounds = [e for e in entries if _request(e).get("method") == "POST"
              and _url(_request(e)["url"]).path == "/game"]
    if not rounds:
        _fail("no_game_transport_observed")
    patterns: Counter[tuple[int, int]] = Counter()
    for entry in rounds:
        req, res = _request(entry), _response(entry)
        if res.get("status") != 200:
            _fail("game_transport_not_200")
        postdata = req.get("postData")
        if not isinstance(postdata, Mapping) or str(postdata.get("mimeType", "")).split(";", 1)[0] != "application/x-www-form-urlencoded":
            _fail("invalid_game_content_type")
        text = postdata.get("text")
        if not isinstance(text, str):
            _fail("missing_game_post_body")
        if _one(text, "sid") != sid:
            _fail("game_session_mismatch")
        try:
            response_data = json.loads(res["content"]["text"])
        except (KeyError, TypeError, ValueError):
            _fail("invalid_game_response")
        if not isinstance(response_data, dict) or "d" not in response_data:
            _fail("missing_game_response_packet")
        when = _entry_time(entry)
        request_bytes = _packet(_one(text, "d"), when)
        response_bytes = _packet(response_data["d"], when)
        patterns[(request_bytes, response_bytes)] += 1

    return {
        "provider": "belatra", "game": game, "language": language,
        "launch_status": launch_res["status"], "game_document_status": 200,
        "datalist_status": 200, "game_transport_posts": len(rounds),
        "packet_size_patterns": [
            {"request_bytes": rq, "response_bytes": rs, "count": count}
            for (rq, rs), count in sorted(patterns.items())
        ],
        "session_continuity": "validated_within_har",
        "packet_framing": "opaque_base64_timestamp_at_bytes_4_7",
        "game_modes": "unclassified", "round_settlement": "not_verified",
        "remote_connector": "not_implemented",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Belatra HAR validation (redacted output)")
    parser.add_argument("har", type=Path)
    args = parser.parse_args()
    try:
        with args.har.open("r", encoding="utf-8") as source:
            report = analyze_har(json.load(source))
    except BelatraContractError as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
