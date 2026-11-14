"""Synthetic-only regression tests; no native session data is stored here."""
import unittest
from copy import deepcopy

from providers.redtiger.session_selector import SessionIdentityError, select_bootstrap_for_round


def bootstrap(session, user, token):
    return {
        "config_response": {
            "table_id": "babylon-riches-table",
            "base_game_id": "babylon-riches-game",
            "wrappedLaunchParams": {"baseUrl": "https://example.invalid"},
        },
        "settings_request": {
            "url": "https://example.invalid/platform/game/settings",
            "body": {
                "token": None, "sessionId": session, "playMode": "demo",
                "gameId": "babylon-riches-game", "userData": {},
                "custom": {}, "listenToFrontend": False,
            },
        },
        "settings_response": {
            "success": True,
            "result": {"user": {"userId": user, "token": token}},
        },
    }


class SessionSelectorTests(unittest.TestCase):
    def setUp(self):
        self.normal = bootstrap("session-normal", "user-normal", "token-normal")
        self.buy = bootstrap("session-buy", "user-buy", "token-buy")
        self.pairs = [self.buy, self.normal]  # intentionally reversed

    def select(self, *, body=None, pairs=None, table="babylon-riches-table", url="https://example.invalid/platform/game/spin"):
        return select_bootstrap_for_round(
            table_id=table,
            financial_url=url,
            financial_body=body or {"gameId": "babylon-riches-game", "userId": "user-normal", "token": "token-normal"},
            bootstraps=self.pairs if pairs is None else pairs,
        )

    def test_normal_and_buy_each_get_own_bootstrap(self):
        self.assertIs(self.select(), self.normal)
        self.assertIs(self.select(body={"gameId":"babylon-riches-game", "userId":"user-buy", "token":"token-buy"}), self.buy)

    def test_stronger_session_id_is_checked_if_present(self):
        self.assertIs(self.select(body={"gameId":"babylon-riches-game", "userId":"user-normal", "token":"token-normal", "sessionId":"session-normal"}), self.normal)
        with self.assertRaisesRegex(SessionIdentityError, "no_matching_native_settings"):
            self.select(body={"gameId":"babylon-riches-game", "userId":"user-normal", "token":"token-normal", "sessionId":"session-buy"})

    def test_mismatching_host_table_game_user_token_rejected(self):
        for changes in (
            {"url": "https://other.invalid/platform/game/spin"},
            {"table": "another-table"},
            {"body": {"gameId":"other-game", "userId":"user-normal", "token":"token-normal"}},
            {"body": {"gameId":"babylon-riches-game", "userId":"other-user", "token":"token-normal"}},
            {"body": {"gameId":"babylon-riches-game", "userId":"user-normal", "token":"wrong-token"}},
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(SessionIdentityError, "no_matching_native_settings"):
                self.select(**changes)

    def test_ambiguous_bootstrap_rejected(self):
        with self.assertRaisesRegex(SessionIdentityError, "ambiguous_native_settings"):
            self.select(pairs=[self.normal, deepcopy(self.normal)])

    def test_missing_financial_identity_rejected(self):
        with self.assertRaisesRegex(SessionIdentityError, "missing_or_invalid_round_token"):
            self.select(body={"gameId":"babylon-riches-game", "userId":"user-normal"})

    def test_non_demo_settings_rejected(self):
        tampered = deepcopy(self.normal)
        tampered["settings_request"]["body"]["playMode"] = "real"
        with self.assertRaisesRegex(SessionIdentityError, "settings_not_verified_demo"):
            self.select(pairs=[tampered])

    def test_endpoint_and_game_contract_rejected(self):
        for field, value in (("gameId", "another-game"),):
            tampered = deepcopy(self.normal)
            tampered["settings_request"]["body"][field] = value
            with self.assertRaisesRegex(SessionIdentityError, "config_settings_game_mismatch"):
                self.select(pairs=[tampered])
        tampered = deepcopy(self.normal)
        tampered["settings_request"]["url"] = "https://other.invalid/platform/game/settings"
        with self.assertRaisesRegex(SessionIdentityError, "settings_endpoint_mismatch"):
            self.select(pairs=[tampered])

    def test_http_not_allowed(self):
        with self.assertRaisesRegex(SessionIdentityError, "invalid_https_host"):
            self.select(url="http://example.invalid/platform/game/spin")


if __name__ == "__main__":
    unittest.main()
