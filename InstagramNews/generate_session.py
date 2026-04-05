"""
Run this script ONCE locally to generate InstagramNews/instagram_session.json.
That file must be committed to the repo so GitHub Actions can reuse the session
without triggering Instagram's challenge_required security block.

BEFORE running this script:
  1. Open the Instagram app on your phone.
  2. If you see any security alerts or "Suspicious activity" warnings, approve them.
  3. Make sure you are logged in and the account is in good standing.

Usage:
    python InstagramNews/generate_session.py

After running:
    git add InstagramNews/instagram_session.json
    git commit -m "Add Instagram session file"
    git push
"""

import os
import time
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    SelectContactPointRecoveryForm,
    RecaptchaChallengeForm,
    BadPassword,
    LoginRequired,
)

SESSION_FILE = os.path.join(os.path.dirname(__file__), "instagram_session.json")

DEVICE_SETTINGS = {
    "app_version": "269.0.0.18.75",
    "android_version": 26,
    "android_release": "8.0.0",
    "dpi": "480dpi",
    "resolution": "1080x1920",
    "manufacturer": "OnePlus",
    "device": "ONEPLUS A3010",
    "model": "OnePlus3T",
    "cpu": "qcom",
    "version_code": "314665256",
}


def challenge_code_handler(username, choice):
    """Called by instagrapi when a verification code is needed."""
    method = {1: "SMS", 2: "email"}.get(choice, f"method {choice}")
    code = input(f"\nInstagram sent a verification code via {method}.\nEnter the code: ").strip()
    return code


def main():
    username = input("Instagram username: ").strip()
    password = input("Instagram password: ").strip()

    cl = Client()
    cl.set_device(DEVICE_SETTINGS)
    cl.challenge_code_handler = challenge_code_handler

    print("\nLogging in (this may take a few seconds)...")
    time.sleep(2)  # Small delay to appear less bot-like

    try:
        cl.login(username, password)
    except ChallengeRequired:
        print("\nInstagram requires a security challenge...")
        api_path = cl.last_json.get("challenge", {}).get("api_path")
        if api_path:
            try:
                cl.challenge_resolve(cl.last_json)
            except SelectContactPointRecoveryForm:
                print("Choose verification method:\n  1. SMS\n  2. Email")
                choice = input("Enter 1 or 2: ").strip()
                cl.challenge_send_code(int(choice))
                code = input("Enter the verification code: ").strip()
                cl.challenge_login_and_process(code)
            except RecaptchaChallengeForm:
                print(
                    "\nERROR: Instagram is requiring a CAPTCHA challenge.\n"
                    "Please:\n"
                    "  1. Open the Instagram app on your phone.\n"
                    "  2. Approve any security prompts.\n"
                    "  3. Wait 30-60 minutes, then retry this script."
                )
                return
        else:
            print(
                "\nERROR: Cannot resolve challenge automatically.\n"
                "Please open the Instagram app and approve any security prompts,\n"
                "then wait a few minutes and retry."
            )
            return
    except BadPassword:
        print("\nERROR: Incorrect password.")
        return
    except LoginRequired:
        print("\nERROR: Login required. The previous session is invalid.")
        return

    cl.dump_settings(SESSION_FILE)
    print(f"\nSession saved to: {SESSION_FILE}")
    print("\nNext steps:")
    print("  git add InstagramNews/instagram_session.json")
    print("  git commit -m 'Add Instagram session file'")
    print("  git push")


if __name__ == "__main__":
    main()
