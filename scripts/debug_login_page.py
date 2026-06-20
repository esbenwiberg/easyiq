#!/usr/bin/env python3
"""Retired helper for the old Aula form-login page."""


def main() -> int:
    """Explain the supported live auth smoke path."""
    print("The old Aula form-login debug flow has been retired.")
    print("Use guardian MitID token state with: python scripts/test_client.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
