import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


LAST_GOOD_PAYLOAD = None
LAST_GOOD_GENERATED_AT = None


def _minutes_to_next_refresh(now: datetime, interval_minutes: int) -> int:
    minute_slot = (now.minute // interval_minutes) * interval_minutes
    current_slot = now.replace(minute=minute_slot, second=0, microsecond=0)
    next_slot = current_slot + timedelta(minutes=interval_minutes)
    return max(0, int((next_slot - now).total_seconds() // 60))


def _parse_rfc3339_utc(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_json_from_s3(s3_client, bucket: str, key: str):
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read()), obj["LastModified"].astimezone(timezone.utc)


def _load_json_from_local(key: str):
    path = Path(key)
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return payload, modified


def _load_team_snapshot(data_source: str, bucket: str, key: str):
    use_s3 = data_source == "s3" or (data_source == "auto" and bucket)
    if use_s3:
        if not bucket:
            raise ValueError("DATA_BUCKET is required when DATA_SOURCE=s3")
        import boto3

        s3_client = boto3.client("s3")
        return _load_json_from_s3(s3_client, bucket, key)
    return _load_json_from_local(key)


def _request_url(event) -> str:
    event = event or {}
    headers = event.get("headers") or {}
    host = headers.get("x-forwarded-host") or headers.get("host") or "pl.itchy7.com"
    path = event.get("rawPath") or "/"
    raw_query = event.get("rawQueryString")
    if raw_query is None:
        raw_query = urlencode((event.get("queryStringParameters") or {}), doseq=True)
    if raw_query:
        return f"https://{host}{path}?{raw_query}"
    return f"https://{host}{path}"


def _resolve_local_tz(event):
    params = (event or {}).get("queryStringParameters") or {}
    tz_name = params.get("tz") or "America/Denver"
    try:
        return ZoneInfo(tz_name), tz_name
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"invalid tz: {tz_name}") from exc


def _resolve_team_filter(event):
    params = (event or {}).get("queryStringParameters") or {}
    value = params.get("team")
    if value is None:
        value = params.get("short_name")
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("invalid team: empty")
    return normalized


def _localize_match_time(value: str, local_tz):
    parsed = _parse_rfc3339_utc(value)
    if parsed is None:
        return None
    return parsed.astimezone(local_tz).strftime("%H:%M")


def _localize_match_datetime(value: str, local_tz):
    parsed = _parse_rfc3339_utc(value)
    if parsed is None:
        return None
    return parsed.astimezone(local_tz)


def _normalize_home_away(value: str):
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if normalized in {"H", "HOME"}:
        return "Home"
    if normalized in {"A", "AWAY"}:
        return "Away"
    if normalized in {"N", "NEUTRAL"}:
        return "Neutral"
    return value


def get_payload(event=None):
    now = datetime.now(timezone.utc)
    local_tz, tz_label = _resolve_local_tz(event)
    team_filter = _resolve_team_filter(event)
    request_url = _request_url(event)
    year = os.environ.get("F1_YEAR", "2026")
    data_source = os.environ.get("DATA_SOURCE", "auto").lower()
    bucket = os.environ.get("DATA_BUCKET")
    snapshot_key = os.environ.get("PL_TEAM_DATA_KEY", f"{year}_pl_team_snapshot.json")

    snapshot, data_last_updated = _load_team_snapshot(data_source, bucket, snapshot_key)
    rows = snapshot.get("teams") or []
    league = snapshot.get("league") or "Premier League"

    teams = []
    for team in rows:
        next_local = _localize_match_datetime(team.get("next_match_time_utc"), local_tz)
        teams.append(
            {
                "ranking": team.get("ranking"),
                "team": team.get("name"),
                "short_name": team.get("short_name"),
                "last_result": team.get("last_result"),
                "last_opponent": team.get("last_opponent"),
                "last_match_time_utc": team.get("last_match_time_utc"),
                "next_opponent": team.get("next_opponent"),
                "next_match_ts_utc": team.get("next_match_time_utc"),
                "next_match_ts_local": _localize_match_time(
                    team.get("next_match_time_utc"), local_tz
                ),
                "next_match_dow": next_local.strftime("%a") if next_local else None,
                "next_match_dom": str(next_local.day) if next_local else None,
                "next_match_home_away": _normalize_home_away(team.get("next_match_home_away")),
            }
        )

    if team_filter is not None:
        teams = [team for team in teams if (team.get("short_name") or "").upper() == team_filter]
        if not teams:
            raise ValueError(f"invalid team: {team_filter}")

    refresh_seconds = 60
    delta_minutes = _minutes_to_next_refresh(now, 5)
    return {
        "general": {
            "source": "pl.itchy7.com",
            "request_url": request_url,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timezone": tz_label,
            "data_last_updated_at": data_last_updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data_age_seconds": max(0, int((now - data_last_updated).total_seconds())),
            "using_last_good": False,
            "refresh": refresh_seconds,
        },
        "endpoint": {
            "method": "GET",
            "path": "/",
            "supported_query_parameters": {
                "tz": "IANA timezone name for dow/dom fields (e.g. America/Los_Angeles)",
                "team": "Team short name filter (e.g. TOT)",
                "short_name": "Alias for team (deprecated)",
            },
        },
        "league": league,
        "teams": teams,
        "meta": {
            "team_count": len(teams),
            "next_refresh_in_minutes": delta_minutes,
        },
    }


def lambda_handler(event, context):
    global LAST_GOOD_PAYLOAD
    global LAST_GOOD_GENERATED_AT
    try:
        payload = get_payload(event)
        LAST_GOOD_PAYLOAD = payload
        LAST_GOOD_GENERATED_AT = datetime.now(timezone.utc)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=0, s-maxage=30, stale-while-revalidate=30",
            },
            "body": json.dumps(payload),
        }
    except ValueError as exc:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }
    except Exception as exc:
        if LAST_GOOD_PAYLOAD is not None and LAST_GOOD_GENERATED_AT is not None:
            payload = json.loads(json.dumps(LAST_GOOD_PAYLOAD))
            general = payload.setdefault("general", {})
            now = datetime.now(timezone.utc)
            general["generated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            general["using_last_good"] = True
            general["fallback_reason"] = str(exc)
            general["last_good_age_seconds"] = max(
                0, int((now - LAST_GOOD_GENERATED_AT).total_seconds())
            )
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Cache-Control": "public, max-age=0, s-maxage=30, stale-while-revalidate=30",
                },
                "body": json.dumps(payload),
            }
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }
