import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1watch.api.premier_league_handler import get_payload, lambda_handler  # noqa: E402


class TestPremierLeagueHandler(unittest.TestCase):
    def test_payload_has_segmented_shape(self):
        payload = get_payload({"queryStringParameters": {"tz": "America/Los_Angeles"}})

        self.assertIn("general", payload)
        self.assertIn("endpoint", payload)
        self.assertIn("schedule", payload)
        self.assertIn("note", payload)
        self.assertEqual(payload["general"]["timezone"], "America/Los_Angeles")
        self.assertIn("request_url", payload["general"])
        self.assertEqual(payload["endpoint"]["method"], "GET")
        self.assertEqual(payload["endpoint"]["path"], "/")
        self.assertIn("tz", payload["endpoint"]["supported_query_parameters"])

    def test_invalid_tz_returns_400(self):
        response = lambda_handler({"queryStringParameters": {"tz": "Not/AZone"}}, None)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
