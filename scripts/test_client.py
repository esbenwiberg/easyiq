#!/usr/bin/env python3
"""
Opt-in live smoke test for the EasyIQ client.

This script expects Aula token state obtained from a completed guardian MitID
flow. It never asks for or uses old form authentication.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import sys


if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


logging.basicConfig(level=logging.DEBUG)


def load_env_file() -> None:
    """Load environment variables from .env."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ[key] = value.strip("\"'")


def load_token_state() -> tuple[str, dict[str, object]]:
    """Load MitID username and Aula token state from the environment."""
    load_env_file()

    username = os.getenv("EASYIQ_MITID_USERNAME")
    access_token = os.getenv("EASYIQ_ACCESS_TOKEN")
    refresh_token = os.getenv("EASYIQ_REFRESH_TOKEN")
    expires_at = os.getenv("EASYIQ_TOKEN_EXPIRES_AT")

    missing = [
        name
        for name, value in {
            "EASYIQ_MITID_USERNAME": username,
            "EASYIQ_ACCESS_TOKEN": access_token,
            "EASYIQ_REFRESH_TOKEN": refresh_token,
            "EASYIQ_TOKEN_EXPIRES_AT": expires_at,
        }.items()
        if not value
    ]
    if missing:
        print(f"Missing live smoke environment fields: {', '.join(missing)}")
        sys.exit(1)

    return username, {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": float(expires_at),
    }


async def main() -> None:
    """Run a live EasyIQ client smoke test."""
    print("Testing EasyIQ client with MitID token state")
    print("=" * 60)

    sys.path.append("custom_components/aula_easyiq")
    from client import EasyIQClient

    username, token_state = load_token_state()
    client = EasyIQClient(username, token_state)

    print(f"Testing with MitID username: {username}")

    try:
        if not client.login():
            print("Authentication failed")
            return

        print("Authentication successful")
        client.get_widgets()
        print(f"Available widgets: {client.widgets}")

        children = await client.get_children()
        print(f"Found {len(children)} children: {[child['name'] for child in children]}")

        if not children:
            print("No children found")
            return

        child = children[0]
        child_id = child["id"]
        child_name = child["name"]

        print(f"\n--- Testing data for {child_name} (ID: {child_id}) ---")

        weekplan_data = await client.get_weekplan(child_id)
        print(f"Weekplan events: {len(weekplan_data.get('events', []))}")

        homework_data = await client.get_homework(child_id)
        print(f"Homework assignments: {len(homework_data.get('assignments', []))}")

        presence_data = await client.get_presence(child_id)
        print(
            "Presence: "
            f"{presence_data.get('status', 'Unknown')} "
            f"(code {presence_data.get('status_code', 'Unknown')})"
        )

        messages_data = await client.get_messages()
        print(f"Messages data available: {bool(messages_data)}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
