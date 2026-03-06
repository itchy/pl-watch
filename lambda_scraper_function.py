import json
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from plwatch.scrapers.premier_league import build_snapshot


def lambda_handler(event, context):
    year = os.environ.get("F1_YEAR", "2026")
    bucket = os.environ.get("DATA_BUCKET")
    if not bucket:
        raise ValueError("DATA_BUCKET is required")
    key = os.environ.get("PL_TEAM_DATA_KEY", f"{year}_pl_team_snapshot.json")

    snapshot = build_snapshot()
    body = (json.dumps(snapshot, separators=(",", ":")) + "\n").encode("utf-8")
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )

    return {
        "status": "ok",
        "bucket": bucket,
        "key": key,
        "generated_at": snapshot.get("generated_at"),
        "size_bytes": len(body),
    }
