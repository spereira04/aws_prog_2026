import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])
BUCKET = os.environ["S3_BUCKET"]

def sanitize(v):
    if isinstance(v, float):
        return Decimal(str(v))
    if isinstance(v, dict):
        return {k: sanitize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [sanitize(i) for i in v]
    return v

def read_s3(key):
    return json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def get_position_at_lap_end(lap, positions, dates):
    if not lap.get("date_start") or lap.get("lap_duration") is None:
        return None
    lap_end = parse_dt(lap["date_start"]) + timedelta(seconds=float(lap["lap_duration"]))
    candidates = [p for p in positions if parse_dt(p["date"]) <= lap_end]
    return candidates[-1]["position"] if candidates else None


def handler(event, context):
    session_key = str(event["detail"]["session_key"])
    drivers = read_s3(f"sessions/{session_key}/drivers/driversRace.json")

    items = []

    session = read_s3(f"sessions/{session_key}/session.json")
    items.append({"PK": f"SESSION#{session_key}", "SK": "#METADATA", **session})

    for driver in drivers:
        driver_number = str(driver["driver_number"])

        positions = read_s3(f"sessions/{session_key}/drivers/{driver_number}/positions.json")
        positions.sort(key=lambda p: p["date"])
        dates = [parse_dt(p["date"]) for p in positions]

        laps = read_s3(f"sessions/{session_key}/drivers/{driver_number}/laps.json")
        laps.sort(key=lambda lap: lap["lap_number"])

        for lap in laps:
            lap["position"] = get_position_at_lap_end(lap, positions, dates)

        timed = [lap for lap in laps if lap.get("lap_duration") and not lap.get("is_pit_out_lap")]
        best = min(timed, key=lambda lap: lap["lap_duration"], default=None)
        speeds = [lap[f] for lap in laps for f in ("i1_speed", "i2_speed", "st_speed") if lap.get(f)]

        items.append({
            "PK": f"SESSION#{session_key}#DRIVER#{driver_number}",
            "SK": "#METADATA",
            **driver,
            "total_laps": len(laps),
            "best_lap_number": best["lap_number"] if best else None,
            "best_lap_duration": Decimal(str(best["lap_duration"])) if best else None,
            "avg_speed": Decimal(str(sum(speeds) / len(speeds))) if speeds else None,
            "max_speed": Decimal(str(max(speeds))) if speeds else None,
        })

        for lap in laps:
            items.append({
                "PK": f"SESSION#{session_key}#DRIVER#{driver_number}",
                "SK": f"LAP#{lap['lap_number']:03d}",
                **lap,
                "lap_duration": Decimal(str(lap["lap_duration"])) if lap.get("lap_duration") else None,
            })

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item={k: sanitize(v) for k, v in item.items() if v is not None})

    logger.info("session=%s items=%d", session_key, len(items))
    return {"session_key": session_key, "items_written": len(items)}
