#!/usr/bin/env python3
"""
setup_kaggle.py — Interactive helper to configure Kaggle API credentials.

Run once before training:
    python backend/setup_kaggle.py
"""

import json
import os
import sys
import stat
from pathlib import Path

KAGGLE_DIR  = Path.home() / ".kaggle"
KAGGLE_JSON = KAGGLE_DIR / "kaggle.json"


def main():
    print("\n" + "=" * 60)
    print("  BuyWise — Kaggle API Setup")
    print("=" * 60)

    if KAGGLE_JSON.exists():
        print(f"\n✅  kaggle.json already exists at: {KAGGLE_JSON}")
        overwrite = input("   Overwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            print("   Keeping existing credentials. You're good to go!")
            sys.exit(0)

    print("""
How to get your Kaggle API token:
  1. Go to  https://www.kaggle.com/settings/account
  2. Scroll to "API" section → click "Create New Token"
  3. A file called 'kaggle.json' will be downloaded.

Paste the contents here (or enter username & key separately):
""")

    choice = input("  [1] Paste full JSON  [2] Enter username+key separately: ").strip()

    if choice == "1":
        print('  Paste the JSON content (e.g. {"username":"xxx","key":"yyy"}) then press Enter:')
        raw = input("  > ").strip()
        try:
            creds = json.loads(raw)
            assert "username" in creds and "key" in creds
        except Exception:
            print("  ❌  Invalid JSON format. Expected: {\"username\":\"...\",\"key\":\"...\"}")
            sys.exit(1)
    else:
        username = input("  Kaggle username: ").strip()
        key      = input("  Kaggle API key: ").strip()
        if not username or not key:
            print("  ❌  Username and key cannot be empty.")
            sys.exit(1)
        creds = {"username": username, "key": key}

    KAGGLE_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_JSON.write_text(json.dumps(creds, indent=2))

    # chmod 600 — required by kaggle library
    os.chmod(KAGGLE_JSON, stat.S_IRUSR | stat.S_IWUSR)

    print(f"\n✅  Credentials saved to: {KAGGLE_JSON}")
    print("   Permissions set to 600 (owner read/write only)")
    print("\n🚀  You can now run the training pipeline:")
    print("     python -m backend.train_with_kaggle\n")


if __name__ == "__main__":
    main()
