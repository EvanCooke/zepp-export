"""CLI for zepp-export.

Usage:
    python -m zepp_export pull --from 2026-02-01 --to 2026-02-07
    python -m zepp_export pull --type heart-rate --from 2026-02-06
    python -m zepp_export export --format csv --from 2026-02-01 --output data.csv
    python -m zepp_export login
    python -m zepp_export status
"""

import argparse
import json
import os
import sys
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from . import __version__
from .client import ZeppClient
from .exceptions import ZeppAuthError, ZeppAPIError
from .export import export_csv, export_apple_health


CONFIG_DIR = Path.home() / ".zepp-export"
CONFIG_FILE = CONFIG_DIR / "config"

DATA_TYPES = ["heart-rate", "sleep", "steps", "stress", "training-load", "sport-load", "all"]


def resolve_credentials():
    """Resolve token and user ID using 12-factor precedence:
    environment variables -> .env -> ~/.zepp-export/config
    """
    load_dotenv()

    token = os.getenv("ZEPP_TOKEN") or os.getenv("HUAMI_APP_TOKEN")
    user_id = os.getenv("ZEPP_USER_ID") or os.getenv("HUAMI_USER_ID")
    base_url = os.getenv("ZEPP_BASE_URL")

    if not token or not user_id:
        if CONFIG_FILE.exists():
            for line in CONFIG_FILE.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key == "ZEPP_TOKEN" and not token:
                    token = value
                elif key == "ZEPP_USER_ID" and not user_id:
                    user_id = value
                elif key == "ZEPP_BASE_URL" and not base_url:
                    base_url = value

    return token, user_id, base_url


def get_client():
    """Create a ZeppClient from resolved credentials."""
    token, user_id, base_url = resolve_credentials()

    if not token or not user_id:
        print("Error: No credentials found.")
        print()
        print("Set them in one of these locations (checked in order):")
        print("  1. Environment variables: ZEPP_TOKEN, ZEPP_USER_ID")
        print("  2. .env file in current directory")
        print("  3. ~/.zepp-export/config")
        print()
        print("Run 'python -m zepp_export login' for setup instructions.")
        sys.exit(1)

    return ZeppClient(token=token, user_id=user_id, base_url=base_url)


def parse_date_range(args):
    """Extract from_date and to_date from parsed args."""
    from_date = getattr(args, "from_date", None) or getattr(args, "from", None)
    to_date = args.to or from_date

    if not from_date:
        from_date = datetime.now().strftime("%Y-%m-%d")
        to_date = from_date

    return from_date, to_date


def count_days(from_date, to_date):
    """Count the number of days in a date range."""
    d1 = datetime.strptime(from_date, "%Y-%m-%d")
    d2 = datetime.strptime(to_date, "%Y-%m-%d")
    return (d2 - d1).days + 1


def iter_dates(from_date, to_date):
    """Yield each date string in a range."""
    d = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")
    while d <= end:
        yield d.strftime("%Y-%m-%d")
        d += timedelta(days=1)


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------

def cmd_pull(args):
    """Pull health data for a date range."""
    client = get_client()
    from_date, to_date = parse_date_range(args)
    data_type = args.type or "all"
    output_dir = args.output or "."
    num_days = count_days(from_date, to_date)

    print(f"Pulling {data_type} data: {from_date} to {to_date} ({num_days} days)")

    if num_days > 30:
        sleep_requests = num_days * 2 if data_type in ("sleep", "all") else 0
        total_requests = num_days + sleep_requests
        est_seconds = total_requests * 0.15
        print(f"Estimated: ~{total_requests} API requests, ~{est_seconds:.0f} seconds")

    all_data = {
        "date_range": {"from": from_date, "to": to_date},
        "extracted_at": datetime.now().isoformat(),
    }

    try:
        if data_type in ("heart-rate", "all"):
            print("\n[Heart Rate]")
            hr_data = {}
            for i, date in enumerate(iter_dates(from_date, to_date)):
                readings = client.get_heart_rate(date)
                hr_data[date] = readings
                count = len(readings)
                print(f"  {date}: {count} readings", end="")
                if count > 0:
                    bpms = [r["bpm"] for r in readings]
                    print(f" (avg {sum(bpms)//len(bpms)}, min {min(bpms)}, max {max(bpms)})")
                else:
                    print()
                if i < num_days - 1:
                    time.sleep(0.1)
            all_data["heart_rate"] = hr_data

        if data_type in ("sleep", "all"):
            print("\n[Sleep]")
            sleep_data = {}
            for i, date in enumerate(iter_dates(from_date, to_date)):
                sleep = client.get_sleep(date)
                sleep_data[date] = sleep
                if sleep:
                    print(f"  {date}: score={sleep.get('sleep_score')} "
                          f"deep={sleep.get('deep_minutes')}min "
                          f"rhr={sleep.get('resting_hr')}bpm")
                else:
                    print(f"  {date}: no sleep data")
                if i < num_days - 1:
                    time.sleep(0.1)
            all_data["sleep"] = sleep_data

        if data_type in ("steps", "all"):
            print("\n[Steps]")
            steps_data = {}
            for i, date in enumerate(iter_dates(from_date, to_date)):
                steps = client.get_steps(date)
                steps_data[date] = steps
                if steps:
                    print(f"  {date}: {steps.get('total_steps')} steps, "
                          f"{steps.get('distance_meters')}m, "
                          f"{steps.get('calories')} cal")
                else:
                    print(f"  {date}: no step data")
                if i < num_days - 1:
                    time.sleep(0.1)
            all_data["steps"] = steps_data

        if data_type in ("stress", "all"):
            print("\n[Stress]")
            stress = client.get_stress(from_date, to_date)
            all_data["stress"] = stress
            for s in stress:
                ts = s.get("timestamp")
                date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else "?"
                print(f"  {date_str}: avg={s.get('avg_stress')} "
                      f"max={s.get('max_stress')} "
                      f"({len(s.get('readings', []))} readings)")
            if not stress:
                print("  No stress data")

        if data_type in ("training-load", "all"):
            print("\n[Training Load]")
            training = client.get_training_load(from_date, to_date)
            all_data["training_load"] = training
            print(f"  {len(training)} records")
            for t in training[-5:]:
                ts = t.get("timestamp")
                date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else "?"
                print(f"  {date_str}: ATL={t.get('atl')} CTL={t.get('ctl')} "
                      f"TSB={t.get('tsb')} score={t.get('exercise_score')}")

        if data_type in ("sport-load", "all"):
            print("\n[Sport Load]")
            sport = client.get_sport_load(from_date, to_date)
            all_data["sport_load"] = sport
            for s in sport[:10]:
                print(f"  {s.get('date')}: load={s.get('daily_load')} "
                      f"weekly={s.get('weekly_load')} "
                      f"optimal={s.get('optimal_min')}-{s.get('optimal_max')}")
            if not sport:
                print("  No sport load data")

    except ZeppAuthError as e:
        print(f"\nAuth error: {e}")
        sys.exit(1)
    except ZeppAPIError as e:
        print(f"\nAPI error: {e}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    filename = f"zepp_{data_type}_{from_date}_to_{to_date}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"\nSaved to {filepath}")


def cmd_export(args):
    """Export previously pulled data or pull + export in one step."""
    client = get_client()
    from_date, to_date = parse_date_range(args)
    fmt = args.format or "json"
    output = args.output
    data_type = args.type or "all"
    num_days = count_days(from_date, to_date)

    print(f"Exporting {data_type} as {fmt}: {from_date} to {to_date} ({num_days} days)")

    if num_days > 30:
        est = num_days * 0.15
        print(f"Estimated: ~{est:.0f} seconds to pull data")

    try:
        if fmt == "csv":
            if not output:
                output = f"zepp_{data_type}_{from_date}_to_{to_date}.csv"

            all_rows = []
            for i, date in enumerate(iter_dates(from_date, to_date)):
                if data_type in ("heart-rate", "all"):
                    readings = client.get_heart_rate(date)
                    for r in readings:
                        all_rows.append({
                            "date": date,
                            "type": "heart_rate",
                            "time": r["time"],
                            "minute": r["minute"],
                            "value": r["bpm"],
                            "unit": "bpm",
                        })

                if data_type in ("steps", "all"):
                    steps = client.get_steps(date)
                    if steps:
                        all_rows.append({
                            "date": date,
                            "type": "steps",
                            "time": "",
                            "minute": "",
                            "value": steps.get("total_steps"),
                            "unit": "steps",
                        })
                        all_rows.append({
                            "date": date,
                            "type": "distance",
                            "time": "",
                            "minute": "",
                            "value": steps.get("distance_meters"),
                            "unit": "meters",
                        })
                        all_rows.append({
                            "date": date,
                            "type": "calories",
                            "time": "",
                            "minute": "",
                            "value": steps.get("calories"),
                            "unit": "kcal",
                        })

                if data_type in ("sleep", "all"):
                    sleep = client.get_sleep(date)
                    if sleep:
                        all_rows.append({
                            "date": date,
                            "type": "sleep_score",
                            "time": "",
                            "minute": "",
                            "value": sleep.get("sleep_score"),
                            "unit": "score",
                        })
                        all_rows.append({
                            "date": date,
                            "type": "resting_hr",
                            "time": "",
                            "minute": "",
                            "value": sleep.get("resting_hr"),
                            "unit": "bpm",
                        })
                        all_rows.append({
                            "date": date,
                            "type": "deep_sleep",
                            "time": "",
                            "minute": "",
                            "value": sleep.get("deep_minutes"),
                            "unit": "minutes",
                        })
                        all_rows.append({
                            "date": date,
                            "type": "light_sleep",
                            "time": "",
                            "minute": "",
                            "value": sleep.get("light_minutes"),
                            "unit": "minutes",
                        })

                print(f"  {date} ({i+1}/{num_days})")
                if i < num_days - 1:
                    time.sleep(0.1)

            if data_type in ("stress", "all"):
                stress = client.get_stress(from_date, to_date)
                for s in stress:
                    for r in s.get("readings", []):
                        ts = r.get("time")
                        dt = datetime.fromtimestamp(ts / 1000) if ts else None
                        all_rows.append({
                            "date": dt.strftime("%Y-%m-%d") if dt else "",
                            "type": "stress",
                            "time": dt.strftime("%H:%M") if dt else "",
                            "minute": "",
                            "value": r.get("value"),
                            "unit": "stress_level",
                        })

            export_csv(all_rows, output)
            print(f"\nExported {len(all_rows)} rows to {output}")

        elif fmt == "apple-health":
            if not output:
                output = f"zepp_apple_health_{from_date}_to_{to_date}.xml"

            hr_data = {}
            steps_dict = {}
            sleep_dict = {}

            for i, date in enumerate(iter_dates(from_date, to_date)):
                if data_type in ("heart-rate", "all"):
                    readings = client.get_heart_rate(date)
                    hr_data[date] = readings

                if data_type in ("steps", "all"):
                    steps = client.get_steps(date)
                    if steps:
                        steps_dict[date] = steps

                if data_type in ("sleep", "all"):
                    sleep = client.get_sleep(date)
                    if sleep:
                        sleep_dict[date] = sleep

                print(f"  {date} ({i+1}/{num_days})")
                if i < num_days - 1:
                    time.sleep(0.1)

            hr_count, steps_count, sleep_count = export_apple_health(
                heart_rate_data=hr_data if hr_data else None,
                steps_data=steps_dict if steps_dict else None,
                sleep_data=sleep_dict if sleep_dict else None,
                filepath=output,
            )

            print(f"\nExported to {output}:")
            print(f"  Heart rate records: {hr_count}")
            print(f"  Step count records: {steps_count}")
            print(f"  Sleep stage records: {sleep_count}")
            print(f"  Total: {hr_count + steps_count + sleep_count} records")
            print()
            print("To import into Apple Health, use a third-party iOS app like")
            print("'Health CSV Importer' or 'Health Auto Export'.")

        elif fmt == "json":
            if not output:
                output = f"zepp_{data_type}_{from_date}_to_{to_date}.json"
            # Delegate to pull with output
            args.output = os.path.dirname(output) or "."
            cmd_pull(args)

        else:
            print(f"Unknown format: {fmt}")
            print("Supported formats: json, csv, apple-health")
            sys.exit(1)

    except ZeppAuthError as e:
        print(f"\nAuth error: {e}")
        sys.exit(1)
    except ZeppAPIError as e:
        print(f"\nAPI error: {e}")
        sys.exit(1)


def cmd_login(args):
    """Guide the user through getting and saving a token."""
    print("zepp-export login")
    print("=" * 40)
    print()
    print("Step 1: Open the Zepp auth page in your browser")
    print("        https://user.huami.com/privacy/index.html")
    print()

    try:
        answer = input("Open in browser now? [Y/n] ").strip().lower()
        if answer != "n":
            webbrowser.open("https://user.huami.com/privacy/index.html")
            print("  Opened! Log in with your Zepp/Amazfit account.")
    except (EOFError, KeyboardInterrupt):
        print()

    print()
    print("Step 2: After logging in, open browser DevTools (F12)")
    print("        Go to Application -> Cookies -> user.huami.com")
    print("        Copy the 'apptoken' cookie value")
    print()

    try:
        token = input("Paste your apptoken: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return

    if not token:
        print("No token entered. Aborted.")
        return

    print()
    print("Step 3: Enter your Zepp user ID")
    print("        (visible in the Zepp app under Profile, or in API responses)")
    print()

    try:
        user_id = input("Your user ID: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return

    if not user_id:
        print("No user ID entered. Aborted.")
        return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        f"# zepp-export credentials\n"
        f"# Saved by 'python -m zepp_export login'\n"
        f"ZEPP_TOKEN={token}\n"
        f"ZEPP_USER_ID={user_id}\n"
    )

    print()
    print(f"Saved to {CONFIG_FILE}")
    print()
    print("Testing connection...")

    try:
        client = ZeppClient(token=token, user_id=user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        steps = client.get_steps(today)
        if steps:
            print(f"  Connected! Today's steps: {steps.get('total_steps')}")
        else:
            print("  Connected! (no step data for today yet)")
        print()
        print("You're all set. Try:")
        print(f"  python -m zepp_export pull --from {today}")
    except ZeppAuthError:
        print("  Token appears invalid or expired. Double-check and try again.")
    except ZeppAPIError as e:
        print(f"  Connection issue: {e}")


def cmd_status(args):
    """Show current credential status and account info."""
    print(f"zepp-export v{__version__}")
    print()

    token, user_id, base_url = resolve_credentials()

    # Show where credentials came from
    load_dotenv()
    env_token = os.getenv("ZEPP_TOKEN") or os.getenv("HUAMI_APP_TOKEN")
    config_token = None
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            if line.startswith("ZEPP_TOKEN="):
                config_token = line.split("=", 1)[1].strip()

    if env_token:
        print(f"Token source: environment / .env")
    elif config_token:
        print(f"Token source: {CONFIG_FILE}")
    else:
        print("Token: NOT FOUND")
        print("Run 'python -m zepp_export login' to set up.")
        return

    print(f"User ID: {user_id or 'NOT FOUND'}")
    print(f"API URL: {base_url or 'https://api-mifit-us2.zepp.com (default)'}")
    print()

    if token and user_id:
        print("Testing connection...")
        try:
            client = ZeppClient(token=token, user_id=user_id, base_url=base_url)
            today = datetime.now().strftime("%Y-%m-%d")
            steps = client.get_steps(today)
            if steps:
                print(f"  Status: Connected")
                print(f"  Today's steps: {steps.get('total_steps')}")
            else:
                print(f"  Status: Connected (no data for today yet)")
        except ZeppAuthError:
            print(f"  Status: TOKEN EXPIRED")
            print(f"  Run 'python -m zepp_export login' to refresh.")
        except ZeppAPIError as e:
            print(f"  Status: Error - {e}")


# ------------------------------------------------------------------
# Argument parser
# ------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="zepp_export",
        description="zepp-export: Access your Amazfit/Zepp health data",
    )
    parser.add_argument("--version", action="version", version=f"zepp-export {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # pull
    pull_parser = subparsers.add_parser("pull", help="Pull health data from Zepp API")
    pull_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD, default: today)")
    pull_parser.add_argument("--to", help="End date (YYYY-MM-DD, default: same as --from)")
    pull_parser.add_argument("--type", choices=DATA_TYPES, default="all",
                            help="Data type to pull (default: all)")
    pull_parser.add_argument("--output", "-o", default=".",
                            help="Output directory (default: current dir)")

    # export
    export_parser = subparsers.add_parser("export", help="Export health data to a file format")
    export_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD, default: today)")
    export_parser.add_argument("--to", help="End date (YYYY-MM-DD, default: same as --from)")
    export_parser.add_argument("--type", choices=DATA_TYPES, default="all",
                              help="Data type to export (default: all)")
    export_parser.add_argument("--format", "-f", choices=["json", "csv", "apple-health"],
                              default="json", help="Output format (default: json)")
    export_parser.add_argument("--output", "-o", help="Output file path")

    # login
    subparsers.add_parser("login", help="Set up Zepp API credentials")

    # status
    subparsers.add_parser("status", help="Show account status and connection info")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "pull":
        cmd_pull(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
