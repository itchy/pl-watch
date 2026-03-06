import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


LAST_GOOD_PAYLOAD = None
LAST_GOOD_GENERATED_AT = None


def _minutes_to_next_refresh(now: datetime, interval_minutes: int) -> int:
    minute_slot = (now.minute // interval_minutes) * interval_minutes
    current_slot = now.replace(minute=minute_slot, second=0, microsecond=0)
    next_slot = current_slot + timedelta(minutes=interval_minutes)
    return max(0, int((next_slot - now).total_seconds() // 60))


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


def get_payload(event=None):
    now = datetime.now(timezone.utc)
    local_tz, tz_label = _resolve_local_tz(event)
    local_now = now.astimezone(local_tz)
    request_url = _request_url(event)
    refresh_seconds = 60
    delta_minutes = _minutes_to_next_refresh(now, 15)
    return {
        "general": {
            "source": "pl.itchy7.com",
            "request_url": request_url,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timezone": tz_label,
            "using_last_good": False,
            "refresh": refresh_seconds,
        },
        "endpoint": {
            "method": "GET",
            "path": "/",
            "supported_query_parameters": {
                "tz": "IANA timezone name for dow/dom fields (e.g. America/Los_Angeles)"
            },
        },
        "schedule": {
            "league": "Premier League",
            "event": "Template",
            "session": "Data Refresh",
            "start": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dow": local_now.strftime("%a"),
            "dom": str(local_now.day),
            "delta": f"{delta_minutes}m",
        },
        "note": "Template endpoint. Replace with real PL fixtures and standings feed.",
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
