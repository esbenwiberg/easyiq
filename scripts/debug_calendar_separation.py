#!/usr/bin/env python3
"""Retired helper for the old calendar separation live debug flow."""


def main() -> int:
    """Explain the supported live auth smoke path."""
    print("This live debug helper used the retired form-auth flow.")
    print("Use guardian MitID token state with: python scripts/test_client.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
