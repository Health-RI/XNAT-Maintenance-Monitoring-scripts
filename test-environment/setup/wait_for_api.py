"""Block until an XNAT REST API answers."""

from __future__ import annotations

import sys
import time

import requests


def wait_for_api(url: str, username: str, password: str, timeout: int = 1800, interval: int = 10) -> None:
    """Poll the projects endpoint until it returns 200, or give up after `timeout`."""
    deadline = time.monotonic() + timeout
    last = "no response yet"

    while time.monotonic() < deadline:
        try:
            response = requests.get(
                f"{url.rstrip('/')}/data/projects",
                params={"format": "json"},
                auth=(username, password),
                timeout=10,
            )
        except requests.RequestException as error:
            last = str(error)
        else:
            if response.status_code == 200:
                print(f"XNAT REST API is up at {url}.")
                return
            last = f"HTTP {response.status_code}"

        print(f"  waiting for {url} ({last})", flush=True)
        time.sleep(interval)

    raise TimeoutError(f"{url} did not answer within {timeout}s (last: {last})")


def wait_for_tomcat(url: str, timeout: int = 1800, interval: int = 10) -> None:
    """Poll until the server responds at all, authenticated or not.

    Used before the bootstrap, when there is no usable admin password yet.
    """
    deadline = time.monotonic() + timeout
    last = "no response yet"

    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=10, allow_redirects=False)
        except requests.RequestException as error:
            last = str(error)
        else:
            if response.status_code < 500:
                print(f"XNAT is responding at {url} (HTTP {response.status_code}).")
                return
            last = f"HTTP {response.status_code}"

        print(f"  waiting for {url} ({last})", flush=True)
        time.sleep(interval)

    raise TimeoutError(f"{url} did not respond within {timeout}s (last: {last})")


if __name__ == "__main__":
    try:
        wait_for_api(sys.argv[1], sys.argv[2], sys.argv[3])
    except TimeoutError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
