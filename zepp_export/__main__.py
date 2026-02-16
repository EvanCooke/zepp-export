"""Entry point for python -m zepp_export."""

import sys


def main():
    print("zepp-export v0.1.0")
    print()
    print("CLI commands are coming in Phase 2. For now, use the library directly:")
    print()
    print("  from zepp_export import ZeppClient")
    print('  client = ZeppClient(token="...", user_id="...")')
    print('  hr = client.get_heart_rate("2026-02-06")')
    print()
    print("Or run the example script:")
    print("  python examples/pull_all_health_data.py 2026-02-06")
    print()
    print("See README.md for full documentation.")


if __name__ == "__main__":
    main()
