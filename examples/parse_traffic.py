#!/usr/bin/env python3
"""
Parse mitmproxy traffic dump and extract all unique Zepp API endpoints.

This is a reference tool used during the reverse-engineering process.
It parses raw mitmdump output and generates a categorized API map.

Usage:
    python parse_traffic.py <path_to_dump.txt> [--output api_map.json]
"""

import re
import json
import sys
from urllib.parse import urlparse, parse_qs
from collections import defaultdict


def parse_dump(filepath):
    """Parse a mitmdump output file and extract unique API endpoints."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    request_pattern = re.compile(
        r"(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(https?://[^\s]+)\s+HTTP"
    )

    requests_found = request_pattern.findall(content)

    endpoints = defaultdict(lambda: {
        "methods": set(),
        "hosts": set(),
        "example_urls": [],
        "params_seen": defaultdict(set),
        "count": 0,
    })

    for url in requests_found:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        if not any(domain in host for domain in [
            "zepp.com", "huami.com", "amazfit.com"
        ]):
            continue

        skip_patterns = [
            "/api/v5/app/collect",
            "/resources/rn/",
            "/discovery/watch/cards/home_",
            "/discovery/watch/cards/splash",
            "/discovery/watch/cards/member",
            "/apps/com.huami.midong/settings",
            "/badge/",
            "/market/",
            "/langpacks/",
            "/user/content/recommend",
            "/devices/ALL/hasNewVersion",
            "/users/messageCenter",
            "/users/training/templates",
            "/thirdParty/",
            "/city/search",
            "/t/posts/",
            "/membership/info",
            "/user/rewards",
        ]

        if any(skip in parsed.path for skip in skip_patterns):
            continue

        method_match = re.search(
            rf"(GET|POST|PUT|DELETE|PATCH)\s+{re.escape(url[:80])}",
            content
        )
        method = method_match.group(1) if method_match else "UNKNOWN"

        path = parsed.path
        path = re.sub(r"/users/\d+/", "/users/{userId}/", path)

        params = parse_qs(parsed.query)
        params.pop("r", None)

        endpoint_key = f"{method} {parsed.scheme}://{host}{path}"

        ep = endpoints[endpoint_key]
        ep["methods"].add(method)
        ep["hosts"].add(host)
        ep["count"] += 1

        if len(ep["example_urls"]) < 3:
            ep["example_urls"].append(url)

        for k, v in params.items():
            for val in v:
                ep["params_seen"][k].add(val)

    return endpoints


def format_report(endpoints):
    """Generate a Markdown report from parsed endpoints."""
    lines = []
    lines.append("# Zepp/Huami API Endpoints - Auto-Generated from Traffic Capture")
    lines.append("")
    lines.append(f"Total unique endpoints found: {len(endpoints)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    categories = {
        "Health Data": [],
        "Events API": [],
        "Sport / Workout": [],
        "User Data": [],
        "Device": [],
        "Other": [],
    }

    for key, ep in sorted(endpoints.items()):
        if "/events" in key:
            categories["Events API"].append((key, ep))
        elif any(x in key for x in ["/heartRate", "/heart_rate", "/band_data", "/sleep", "/SEC_HR", "/weightRecord"]):
            categories["Health Data"].append((key, ep))
        elif any(x in key for x in ["/sport", "/WatchSport", "/run/"]):
            categories["Sport / Workout"].append((key, ep))
        elif any(x in key for x in ["/users/", "/huami.health"]):
            categories["User Data"].append((key, ep))
        elif any(x in key for x in ["/device", "/files/"]):
            categories["Device"].append((key, ep))
        else:
            categories["Other"].append((key, ep))

    for category, eps in categories.items():
        if not eps:
            continue

        lines.append(f"## {category}")
        lines.append("")

        for key, ep in eps:
            lines.append(f"### `{key}`")
            lines.append("")
            lines.append(f"- **Times called**: {ep['count']}")
            lines.append(f"- **Host(s)**: {', '.join(ep['hosts'])}")
            lines.append("")

            if ep["params_seen"]:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Parameter | Example Values |")
                lines.append("|-----------|---------------|")
                for param, values in sorted(ep["params_seen"].items()):
                    example_vals = ", ".join(list(values)[:5])
                    if len(values) > 5:
                        example_vals += f" ... ({len(values)} total)"
                    lines.append(f"| `{param}` | `{example_vals}` |")
                lines.append("")

            if ep["example_urls"]:
                lines.append("**Example URL:**")
                lines.append("```")
                lines.append(ep["example_urls"][0])
                lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def export_json(endpoints, filepath):
    """Export endpoint data to JSON."""
    serializable = {}
    for key, ep in endpoints.items():
        serializable[key] = {
            "methods": list(ep["methods"]),
            "hosts": list(ep["hosts"]),
            "count": ep["count"],
            "example_urls": ep["example_urls"],
            "params": {k: list(v) for k, v in ep["params_seen"].items()},
        }

    with open(filepath, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"JSON exported to {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_traffic.py <dump_file.txt> [--output api_map.json]")
        sys.exit(1)

    filepath = sys.argv[1]
    output_json = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output_json = sys.argv[idx + 1]

    print(f"Parsing {filepath}...")
    endpoints = parse_dump(filepath)
    print(f"Found {len(endpoints)} unique API endpoints")

    report = format_report(endpoints)

    report_path = filepath.replace(".txt", "_api_map.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Markdown report saved to {report_path}")

    if output_json:
        export_json(endpoints, output_json)

    print("\n" + "=" * 60)
    print(report)


if __name__ == "__main__":
    main()
