import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1watch.api.premier_league_handler import get_payload, lambda_handler  # noqa: E402


class TestPremierLeagueHandler(unittest.TestCase):
    def _with_local_snapshot(self):
        tmp = tempfile.TemporaryDirectory()
        snapshot_path = Path(tmp.name) / "snapshot.json"
        snapshot = {
            "league": "Premier League",
            "teams": [
                {
                    "name": "Arsenal",
                    "short_name": "ARS",
                    "last_result": "W",
                    "last_opponent": "Chelsea",
                    "last_match_time_utc": "2026-03-01T16:30:00Z",
                    "next_opponent": "Tottenham",
                    "next_match_time_utc": "2026-03-14T15:00:00Z",
                    "next_match_home_away": "H",
                }
            ],
        }
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

        old_env = {
            "DATA_SOURCE": os.environ.get("DATA_SOURCE"),
            "PL_TEAM_DATA_KEY": os.environ.get("PL_TEAM_DATA_KEY"),
        }
        os.environ["DATA_SOURCE"] = "local"
        os.environ["PL_TEAM_DATA_KEY"] = str(snapshot_path)
        return tmp, old_env

    def test_payload_has_segmented_shape(self):
        tmp, old_env = self._with_local_snapshot()
        try:
            payload = get_payload({"queryStringParameters": {"tz": "America/Los_Angeles"}})
        finally:
            tmp.cleanup()
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertIn("general", payload)
        self.assertIn("endpoint", payload)
        self.assertIn("teams", payload)
        self.assertIn("meta", payload)
        self.assertEqual(payload["general"]["timezone"], "America/Los_Angeles")
        self.assertIn("request_url", payload["general"])
        self.assertEqual(payload["endpoint"]["method"], "GET")
        self.assertEqual(payload["endpoint"]["path"], "/")
        self.assertIn("tz", payload["endpoint"]["supported_query_parameters"])
        self.assertEqual(payload["teams"][0]["team"], "Arsenal")
        self.assertEqual(payload["teams"][0]["last_result"], "W")
        self.assertEqual(payload["teams"][0]["next_opponent"], "Tottenham")
        self.assertTrue(payload["teams"][0]["next_match_time_local"].endswith("-0700"))

    def test_invalid_tz_returns_400(self):
        tmp, old_env = self._with_local_snapshot()
        try:
            response = lambda_handler({"queryStringParameters": {"tz": "Not/AZone"}}, None)
        finally:
            tmp.cleanup()
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
