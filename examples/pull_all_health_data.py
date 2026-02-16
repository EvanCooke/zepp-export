#!/usr/bin/env python3
"""
Zepp Health Data Extractor -- Example Script

Pulls all available health data from the Zepp/Huami Cloud API using the
zepp-export library. Demonstrates every data source.

Usage:
    python pull_all_health_data.py                         # today's data
    python pull_all_health_data.py 2026-02-06              # specific date
    python pull_all_health_data.py 2026-02-01 2026-02-07   # date range

Setup:
    1. Copy .env.example to .env and fill in your token and user ID
    2. pip install -e .  (from the repo root)
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from zepp_export import ZeppClient, ZeppAuthError, ZeppAPIError

load_dotenv()


def main():
    # Resolve token: env vars -> .env -> config file (12-factor order)
    token = os.getenv("ZEPP_TOKEN") or os.getenv("HUAMI_APP_TOKEN")
    user_id = os.getenv("ZEPP_USER_ID") or os.getenv("HUAMI_USER_ID")
    base_url = os.getenv("ZEPP_BASE_URL")

    if not token or not user_id:
        print("ERROR: Set ZEPP_TOKEN and ZEPP_USER_ID in your .env file")
        print("See .env.example for details")
        sys.exit(1)

    # Parse date arguments
    if len(sys.argv) >= 3:
        from_date = sys.argv[1]
        to_date = sys.argv[2]
    elif len(sys.argv) == 2:
        from_date = sys.argv[1]
        to_date = sys.argv[1]
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        from_date = today
        to_date = today

    print("Zepp Health Data Extractor")
    print(f"Date range: {from_date} to {to_date}")
    print(f"User ID: {user_id}")

    try:
        client = ZeppClient(token=token, user_id=user_id, base_url=base_url)
    except ZeppAuthError as e:
        print(f"Auth error: {e}")
        sys.exit(1)

    all_data = {
        "date_range": {"from": from_date, "to": to_date},
        "extracted_at": datetime.now().isoformat(),
    }

    # 1. Heart rate
    print(f"\n{'='*60}")
    print("[HEART RATE]")
    print(f"{'='*60}")
    try:
        hr = client.get_heart_rate(from_date)
        all_data["heart_rate_count"] = len(hr)
        if hr:
            bpms = [r["bpm"] for r in hr]
            print(f"  Readings: {len(hr)}")
            print(f"  Min: {min(bpms)} bpm")
            print(f"  Max: {max(bpms)} bpm")
            print(f"  Avg: {sum(bpms) // len(bpms)} bpm")
        else:
            print("  No heart rate data")
    except (ZeppAPIError, ZeppAuthError) as e:
        print(f"  Error: {e}")

    # 2. Sleep
    print(f"\n{'='*60}")
    print("[SLEEP]")
    print(f"{'='*60}")
    try:
        sleep = client.get_sleep(from_date)
        all_data["sleep"] = sleep
        if sleep:
            print(f"  Score: {sleep.get('sleep_score')}")
            print(f"  Resting HR: {sleep.get('resting_hr')} bpm")
            print(f"  Deep: {sleep.get('deep_minutes')} min")
            print(f"  Light: {sleep.get('light_minutes')} min")
            if "duration_minutes" in sleep:
                print(f"  Duration: {sleep['duration_minutes']} min ({sleep['duration_minutes']/60:.1f} hrs)")
            print(f"  Stages: {len(sleep.get('stages', []))} segments")
            print(f"  (fetched from: {sleep.get('fetched_from')})")
        else:
            print("  No sleep data (try the previous day)")
    except (ZeppAPIError, ZeppAuthError) as e:
        print(f"  Error: {e}")

    # 3. Steps
    print(f"\n{'='*60}")
    print("[STEPS]")
    print(f"{'='*60}")
    try:
        steps = client.get_steps(from_date)
        all_data["steps"] = steps
        if steps:
            print(f"  Total: {steps.get('total_steps')}")
            print(f"  Distance: {steps.get('distance_meters')}m")
            print(f"  Calories: {steps.get('calories')}")
            print(f"  Goal: {steps.get('goal')}")
        else:
            print("  No step data")
    except (ZeppAPIError, ZeppAuthError) as e:
        print(f"  Error: {e}")

    # 4. Stress
    print(f"\n{'='*60}")
    print("[STRESS]")
    print(f"{'='*60}")
    try:
        stress = client.get_stress(from_date, to_date)
        all_data["stress"] = stress
        for s in stress:
            print(f"  Avg: {s.get('avg_stress')}  Max: {s.get('max_stress')}  Min: {s.get('min_stress')}")
            zones = s.get("zone_percentages", {})
            print(f"  Zones: Relaxed={zones.get('relaxed')}%  Normal={zones.get('normal')}%  "
                  f"Medium={zones.get('medium')}%  High={zones.get('high')}%")
            print(f"  Readings: {len(s.get('readings', []))} (5-min intervals)")
        if not stress:
            print("  No stress data")
    except (ZeppAPIError, ZeppAuthError) as e:
        print(f"  Error: {e}")

    # 5. Training load
    print(f"\n{'='*60}")
    print("[TRAINING LOAD]")
    print(f"{'='*60}")
    try:
        training = client.get_training_load(from_date, to_date)
        all_data["training_load_count"] = len(training)
        print(f"  Found {len(training)} records")
        for t in training[-3:]:
            print(f"  ATL={t.get('atl')}  CTL={t.get('ctl')}  TSB={t.get('tsb')}  "
                  f"Score={t.get('exercise_score')}")
    except (ZeppAPIError, ZeppAuthError) as e:
        print(f"  Error: {e}")

    # 6. Sport load
    print(f"\n{'='*60}")
    print("[SPORT LOAD]")
    print(f"{'='*60}")
    try:
        sport = client.get_sport_load(from_date, to_date)
        all_data["sport_load"] = sport
        for s in sport[:5]:
            print(f"  {s.get('date')}  Load={s.get('daily_load')}  "
                  f"Weekly={s.get('weekly_load')}  "
                  f"Optimal={s.get('optimal_min')}-{s.get('optimal_max')}")
        if not sport:
            print("  No sport load data")
    except (ZeppAPIError, ZeppAuthError) as e:
        print(f"  Error: {e}")

    # Export
    export_file = f"health_data_{from_date}_to_{to_date}.json"
    with open(export_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"DONE! Data saved to {export_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
