"""Synthetic, reproducible fixtures spanning the Postman window and rolling 90 days."""

import os
from datetime import UTC, datetime, timedelta

ASSETS: list[dict] = [
    {
        "asset_id": "BFP-101",
        "asset_name": "Boiler Feed Pump 101",
        "unit": "Unit 1",
        "site": "NorthPlant",
        "criticality": 5,
    },
    {
        "asset_id": "BFP-102",
        "asset_name": "Boiler Feed Pump 102",
        "unit": "Unit 2",
        "site": "NorthPlant",
        "criticality": 4,
    },
    *[
        {
            "asset_id": f"CMP-{i}",
            "asset_name": f"Compressor {i}",
            "unit": "Unit 3",
            "site": "SouthPlant",
            "criticality": 4,
        }
        for i in range(201, 204)
    ],
    {
        "asset_id": "VAL-401",
        "asset_name": "Control Valve 401",
        "unit": "Unit 4",
        "site": "SouthPlant",
        "criticality": 3,
    },
    *[
        {
            "asset_id": f"MOT-{i}",
            "asset_name": f"Motor {i}",
            "unit": "Unit 5",
            "site": "EastRefinery",
            "criticality": 5,
        }
        for i in range(501, 504)
    ],
]
NOW = datetime.fromisoformat(os.getenv("SIMULATOR_NOW", datetime.now(UTC).isoformat()))


def make_alarms():
    rows = []
    # Historical contract window plus current rolling-window observations.
    anchors = [datetime(2026, 6, 1, tzinfo=UTC), NOW - timedelta(days=30)]
    for period, anchor in enumerate(anchors):
        for asset in ASSETS:
            for i in range(24):
                start = anchor + timedelta(days=i // 12, minutes=i % 12)
                rows.append(
                    {
                        **asset,
                        "alarm_id": f"{asset['asset_id']}-{period}-{i:03}",
                        "alarm_name": [
                            "High vibration",
                            "Low suction pressure",
                            "Bearing temperature high",
                        ][i % 3],
                        "severity": ["critical", "high", "medium"][i % 3],
                        "alarm_type": ["safety", "process", "device"][i % 3],
                        "status": "active" if i % 4 == 0 else "cleared",
                        "start_time": start.isoformat(),
                        "ack_delay_seconds": 30 + i * 15,
                        "duration_minutes": 200 if i % 4 == 0 else 15 + i,
                    }
                )
    return rows


ALARMS = make_alarms()
