"""Synthetic-only Belatra fixtures. The SID is fabricated, not from any HAR."""
import base64
from copy import deepcopy
from datetime import datetime
import json
import unittest
from urllib.parse import urlencode

from providers.belatra.har_contract import BelatraContractError, analyze_har

STAMP = "2026-11-14T10:38:33+00:00"
EPOCH = int(datetime.fromisoformat(STAMP).timestamp())
SID = "example-demo-id-not-valid"


def packet(epoch=EPOCH):
    data = b"\x00\x01\x02\x03" + epoch.to_bytes(4, "little") + b"\x01\x02\x03"
    return base64.b64encode(data).decode()


def entry(method, path, status, *, headers=None, request_body=None, response_body=None, mime=None):
    req = {"method": method, "url": "https://demo.bltrm.com" + path}
    if request_body is not None:
        req["postData"] = {"text": request_body, "mimeType": mime}
    res = {"status": status, "headers": headers or [], "content": {"text": response_body or ""}}
    return {"startedDateTime": STAMP, "request": req, "response": res}


def synthetic():
    return {"log": {"entries": [
        entry("GET", "/belatra/demo?game=mr_ferret&language=es", 302,
              headers=[{"name": "Location", "value": "/?modification=mr_ferret&sid=" + SID}]),
        entry("GET", "/?modification=mr_ferret&sid=" + SID, 200),
        entry("POST", "/user/datalist", 200,
              request_body=json.dumps({"datatype": "gamename", "sid": SID}), mime="application/json"),
        entry("POST", "/game", 200,
              request_body=urlencode({"sid": SID, "d": packet()}),
              response_body=json.dumps({"d": packet()}), mime="application/x-www-form-urlencoded"),
    ]}}


class BelatraHarTests(unittest.TestCase):
    def test_valid_synthetic_demo(self):
        r = analyze_har(synthetic())
        self.assertEqual((r["game"], r["language"], r["game_transport_posts"]), ("mr_ferret", "es", 1))
        self.assertEqual(r["game_modes"], "unclassified")
        self.assertEqual(r["round_settlement"], "not_verified")

    def test_report_never_exposes_sid_or_packet(self):
        report = json.dumps(analyze_har(synthetic()))
        self.assertNotIn(SID, report)
        self.assertNotIn(packet(), report)
        self.assertNotIn("cookies", report.lower())

    def test_game_session_crossed(self):
        h = synthetic()
        h["log"]["entries"][-1]["request"]["postData"]["text"] = urlencode({"sid": "different", "d": packet()})
        with self.assertRaisesRegex(BelatraContractError, "game_session_mismatch"):
            analyze_har(h)

    def test_datalist_session_crossed(self):
        h = synthetic()
        h["log"]["entries"][2]["request"]["postData"]["text"] = json.dumps({"datatype": "gamename", "sid": "different"})
        with self.assertRaisesRegex(BelatraContractError, "datalist_session_mismatch"):
            analyze_har(h)

    def test_untrusted_redirect(self):
        h = synthetic()
        h["log"]["entries"][0]["response"]["headers"][0]["value"] = "https://evil.invalid/?sid=bad&modification=mr_ferret"
        with self.assertRaisesRegex(BelatraContractError, "untrusted_demo_host"):
            analyze_har(h)

    def test_invalid_base64(self):
        h = synthetic()
        h["log"]["entries"][-1]["response"]["content"]["text"] = json.dumps({"d": "not base64 !"})
        with self.assertRaisesRegex(BelatraContractError, "packet_not_base64"):
            analyze_har(h)

    def test_packet_timestamp_mismatch(self):
        h = synthetic()
        h["log"]["entries"][-1]["response"]["content"]["text"] = json.dumps({"d": packet(1000000000)})
        with self.assertRaisesRegex(BelatraContractError, "packet_epoch_mismatch"):
            analyze_har(h)

    def test_http_200_is_not_settlement(self):
        h = synthetic()
        h["log"]["entries"][-1]["response"]["status"] = 403
        with self.assertRaisesRegex(BelatraContractError, "game_transport_not_200"):
            analyze_har(h)

    def test_missing_launch(self):
        h = synthetic()
        del h["log"]["entries"][0]
        with self.assertRaisesRegex(BelatraContractError, "missing_or_duplicate_belatra_demo_step"):
            analyze_har(h)

    def test_no_game_transport(self):
        h = synthetic()
        del h["log"]["entries"][-1]
        with self.assertRaisesRegex(BelatraContractError, "no_game_transport_observed"):
            analyze_har(h)

    def test_duplicate_launch(self):
        h = synthetic()
        h["log"]["entries"].append(deepcopy(h["log"]["entries"][0]))
        with self.assertRaisesRegex(BelatraContractError, "missing_or_duplicate_belatra_demo_step"):
            analyze_har(h)


if __name__ == "__main__":
    unittest.main()
