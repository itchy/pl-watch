import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import requests


BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"


def _parse_kickoff(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _match_result(team_id: int, fixture: dict):
    home_id = fixture.get("team_h")
    away_id = fixture.get("team_a")
    home_score = fixture.get("team_h_score")
    away_score = fixture.get("team_a_score")
    if home_score is None or away_score is None:
        return None

    if team_id == home_id:
        if home_score > away_score:
            return "W"
        if home_score < away_score:
            return "L"
        return "D"
    if team_id == away_id:
        if away_score > home_score:
            return "W"
        if away_score < home_score:
            return "L"
        return "D"
    return None


def _opponent(team_id: int, fixture: dict, team_name_by_id: dict):
    home_id = fixture.get("team_h")
    away_id = fixture.get("team_a")
    if team_id == home_id:
        return team_name_by_id.get(away_id), "H"
    if team_id == away_id:
        return team_name_by_id.get(home_id), "A"
    return None, None


def build_snapshot():
    bootstrap = requests.get(BOOTSTRAP_URL, timeout=20)
    bootstrap.raise_for_status()
    fixtures_resp = requests.get(FIXTURES_URL, timeout=20)
    fixtures_resp.raise_for_status()

    bootstrap_json = bootstrap.json()
    fixtures = fixtures_resp.json()
    teams = bootstrap_json.get("teams") or []

    team_name_by_id = {team["id"]: team["name"] for team in teams}
    now = datetime.now(timezone.utc)

    finished_fixtures = []
    upcoming_fixtures = []
    for fixture in fixtures:
        kickoff = _parse_kickoff(fixture.get("kickoff_time"))
        if kickoff is None:
            continue
        entry = {"kickoff": kickoff, "fixture": fixture}
        if fixture.get("finished") is True:
            finished_fixtures.append(entry)
        elif kickoff >= now:
            upcoming_fixtures.append(entry)

    finished_fixtures.sort(key=lambda row: row["kickoff"], reverse=True)
    upcoming_fixtures.sort(key=lambda row: row["kickoff"])

    rows = []
    for team in sorted(teams, key=lambda item: item["name"]):
        team_id = team["id"]
        last_fixture = next(
            (
                row
                for row in finished_fixtures
                if team_id in (row["fixture"].get("team_h"), row["fixture"].get("team_a"))
            ),
            None,
        )
        next_fixture = next(
            (
                row
                for row in upcoming_fixtures
                if team_id in (row["fixture"].get("team_h"), row["fixture"].get("team_a"))
            ),
            None,
        )

        last_result = None
        last_opponent = None
        last_match_time_utc = None
        if last_fixture:
            fixture = last_fixture["fixture"]
            last_result = _match_result(team_id, fixture)
            last_opponent, _ = _opponent(team_id, fixture, team_name_by_id)
            last_match_time_utc = last_fixture["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ")

        next_opponent = None
        next_match_time_utc = None
        next_match_home_away = None
        if next_fixture:
            fixture = next_fixture["fixture"]
            next_opponent, next_match_home_away = _opponent(team_id, fixture, team_name_by_id)
            next_match_time_utc = next_fixture["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ")

        rows.append(
            {
                "team_id": team_id,
                "name": team["name"],
                "short_name": team.get("short_name"),
                "last_result": last_result,
                "last_opponent": last_opponent,
                "last_match_time_utc": last_match_time_utc,
                "next_opponent": next_opponent,
                "next_match_time_utc": next_match_time_utc,
                "next_match_home_away": next_match_home_away,
            }
        )

    return {
        "league": "Premier League",
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_endpoints": [BOOTSTRAP_URL, FIXTURES_URL],
        "teams": rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Build per-team PL last/next fixture snapshot")
    parser.add_argument("--year", type=int, required=True, help="Used in output filename only")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.year}_pl_team_snapshot.json"
    backup_file = output_file.with_suffix(".json.bak")

    if output_file.exists():
        shutil.copy2(output_file, backup_file)
        print(f"Backed up {output_file} to {backup_file}")

    try:
        data = build_snapshot()
        output_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {output_file}")
    except Exception as exc:
        print(f"Error: {exc}")
        if backup_file.exists():
            shutil.copy2(backup_file, output_file)
            print(f"Restored {output_file} from backup")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
