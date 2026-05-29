"""Command-line probe: test the zeversolar library against a real inverter.

Usage:
    python probe.py <host> [--write]
    python probe.py 192.168.2.22
    python probe.py 192.168.2.22 --write   # also tests write path (restores state)

Read-only by default. Pass --write to also exercise set_power_limit, which
will temporarily change the limit to 90% and then restore the original value.
The device is always left in the state it was found in.
"""

import sys
import time
import dataclasses
import urllib.parse

import requests

from zeversolar import ZeverSolarClient, ZeverSolarPowerLimitData
from zeversolar.exceptions import ZeverSolarInvalidData, ZeverSolarPowerLimitNotSupported


def fetch_raw(host: str, path: str) -> str:
    """Fetch a raw CGI endpoint and return the response body."""
    netloc = urllib.parse.urlparse(f"http://{host}").netloc or host
    url = f"http://{netloc}/{path}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def print_fields(obj: object) -> None:
    for field in dataclasses.fields(obj):  # type: ignore[arg-type]
        print(f"  {field.name}: {getattr(obj, field.name)}")


def wait_for_limit(client: ZeverSolarClient, target_pct: int, timeout: int = 120) -> bool:
    """Poll get_power_limit() until it reaches target_pct or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = client.get_power_limit().limit_pct
        print(f"  ... {current}%")
        if current == target_pct:
            return True
        time.sleep(5)
    return False


def test_write(client: ZeverSolarClient, original: ZeverSolarPowerLimitData) -> None:
    """Exercise set_power_limit and restore state unconditionally."""
    target = 90 if original.limit_pct != 90 else 80
    print(f"\n=== set_power_limit({target}%) ===")
    print(f"  Saving original: limit_pct={original.limit_pct}, mode={original.mode}")
    try:
        client.set_power_limit(target)
        if wait_for_limit(client, target):
            print("  Write verified ✓")
        else:
            print(f"  Timed out waiting for {target}%")
    finally:
        print(f"\n=== Restoring original limit ({original.limit_pct}%) ===")
        client.set_power_limit(original.limit_pct)
        if wait_for_limit(client, original.limit_pct):
            print("  Restore verified ✓")
        else:
            print(f"  WARNING: restore timed out (readback may not be {original.limit_pct}%)")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python probe.py <host> [--write]")
        print("Example: python probe.py 192.168.2.22")
        sys.exit(1)

    host = sys.argv[1]
    write_mode = "--write" in sys.argv
    print(f"Connecting to {host} ...\n")

    client = ZeverSolarClient(host=host)

    print("=== get_data() ===")
    data = client.get_data()
    print_fields(data)

    print("\n=== get_power_limit() ===")
    original_limit = None
    try:
        original_limit = client.get_power_limit()
        print_fields(original_limit)
    except ZeverSolarPowerLimitNotSupported:
        print("  Not supported by this inverter.")
    except ZeverSolarInvalidData:
        print("  ZeverSolarInvalidData — raw adv.cgi response follows for diagnosis:")
        try:
            raw = fetch_raw(host, "adv.cgi")
            for i, line in enumerate(raw.splitlines()):
                print(f"  line {i:2d}: {line!r}")
        except Exception as exc:
            print(f"  Could not fetch adv.cgi: {exc}")

    if write_mode:
        if original_limit is None:
            print("\n--write skipped: get_power_limit() failed above.")
        else:
            test_write(client, original_limit)


if __name__ == "__main__":
    main()
