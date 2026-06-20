#!/usr/bin/env python3
"""Retired helper for the old presence form-login smoke test."""


def main() -> int:
    """Explain the supported live auth smoke path."""
    print("The old presence smoke test has been retired.")
    print("Use guardian MitID token state with: python scripts/test_client.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
