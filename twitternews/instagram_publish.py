"""
Publish the daily image to Instagram with the official Graph API (Instagram Content Publishing).

Two steps, run by the workflow after the pipeline:
  1. --upload: attach the JPEG to a GitHub release (tag INSTAGRAM_RELEASE_TAG), delete the images
     from earlier runs, and record the public download URL in latest.json.
  2. (no flag): create an Instagram media container from that URL, wait until Instagram has
     fetched and processed it, then publish it.

Instagram fetches the image itself, so the URL must be public while the container is created.
Instagram keeps its own copy after publishing, so the old release assets can be deleted.

Required environment variables:
  GITHUB_REPOSITORY       set by GitHub Actions (OWNER/REPO); used to build the download URL
  GH_TOKEN                GitHub token for the gh CLI (uploading to the release)
  INSTAGRAM_USER_ID       ID of the Instagram Professional account
  INSTAGRAM_ACCESS_TOKEN  Long-lived access token with instagram_content_publish permission
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import requests

GRAPH_VERSION = "v23.0"
# Instagram API with Instagram Login: the token from the Meta app is an Instagram user token
GRAPH_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"
INSTAGRAM_RELEASE_TAG = "instagram-images"

POSTS_DIR = os.path.join(tempfile.gettempdir(), "twitternews_posts")
LATEST_POST = os.path.join(POSTS_DIR, "latest.json")

READY_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 5


def _gh(*args: str) -> str:
    """Run a gh CLI command and return its stdout. Raises with gh's error message on failure."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def _load_latest() -> dict:
    with open(LATEST_POST, encoding="utf-8") as f:
        return json.load(f)


def _save_latest(post: dict) -> None:
    with open(LATEST_POST, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)


def upload_image_to_release(repo: str) -> str:
    """Upload the latest image to the release, delete older images, and return its public URL."""
    post = _load_latest()
    image_path = post["image"]
    name = os.path.basename(image_path)

    # Create the release on first use. It is not marked as "latest", so the repo's latest release is unchanged.
    try:
        _gh("release", "view", INSTAGRAM_RELEASE_TAG, "--repo", repo)
    except RuntimeError:
        _gh("release", "create", INSTAGRAM_RELEASE_TAG, "--repo", repo, "--latest=false",
            "--title", "Instagram post images",
            "--notes", "Images used for the daily Instagram post. Older images are removed automatically.")

    _gh("release", "upload", INSTAGRAM_RELEASE_TAG, image_path, "--repo", repo)
    print(f"[instagram] uploaded {name} to release '{INSTAGRAM_RELEASE_TAG}'")

    # Remove images from earlier runs. Only this run's image is kept.
    assets = json.loads(_gh("release", "view", INSTAGRAM_RELEASE_TAG, "--repo", repo, "--json", "assets"))["assets"]
    for asset in assets:
        if asset["name"] != name and asset["name"].endswith(".jpg"):
            _gh("release", "delete-asset", INSTAGRAM_RELEASE_TAG, asset["name"], "--repo", repo, "--yes")
            print(f"[instagram] removed old image: {asset['name']}")

    url = f"https://github.com/{repo}/releases/download/{INSTAGRAM_RELEASE_TAG}/{name}"
    post["image_url"] = url
    _save_latest(post)
    print(f"[instagram] image URL: {url}")
    return url


def _check(resp: requests.Response) -> None:
    """Raise with the Graph API's error message, which raise_for_status() would hide."""
    if not resp.ok:
        raise RuntimeError(f"Graph API error {resp.status_code}: {resp.text}")


def create_container(user_id: str, token: str, image_url: str, caption: str) -> str:
    """Step 1: create a media container for the image. Returns the container ID."""
    resp = requests.post(
        f"{GRAPH_URL}/{user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    _check(resp)
    return resp.json()["id"]


def wait_until_ready(container_id: str, token: str) -> None:
    """Poll the container until Instagram has fetched and processed the image."""
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while True:
        resp = requests.get(
            f"{GRAPH_URL}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        _check(resp)
        data = resp.json()
        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {status}: {data.get('status')}")
        if time.time() > deadline:
            raise TimeoutError(f"Instagram container not ready after {READY_TIMEOUT_SECONDS}s (status {status})")
        time.sleep(POLL_INTERVAL_SECONDS)


def publish_container(user_id: str, token: str, container_id: str) -> str:
    """Step 2: publish the ready container. Returns the published media ID."""
    resp = requests.post(
        f"{GRAPH_URL}/{user_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    _check(resp)
    return resp.json()["id"]


def publish_image(user_id: str, token: str, image_url: str, caption: str) -> str:
    """Create, wait for and publish one image post. Returns the Instagram media ID."""
    container_id = create_container(user_id, token, image_url, caption)
    print(f"[instagram] container created: {container_id}")
    wait_until_ready(container_id, token)
    media_id = publish_container(user_id, token, container_id)
    print(f"[instagram] published media ID: {media_id}")
    return media_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the latest post image to Instagram")
    parser.add_argument("--upload", action="store_true", help="Upload the image to the GitHub release instead of publishing")
    args = parser.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY")
    if args.upload:
        if not repo:
            print("GITHUB_REPOSITORY is not set.")
            return 1
        try:
            upload_image_to_release(repo)
        except (RuntimeError, OSError, KeyError) as e:
            print(f"[instagram] upload failed: {e}")
            return 1
        return 0

    user_id = os.environ.get("INSTAGRAM_USER_ID")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not user_id or not token:
        # Not configured yet: skip instead of failing the run, so the X post and history still complete
        print("[instagram] INSTAGRAM_USER_ID or INSTAGRAM_ACCESS_TOKEN not set. Skipping Instagram post.")
        return 0

    try:
        post = _load_latest()
        publish_image(user_id, token, post["image_url"], post["caption"])
    except (requests.RequestException, RuntimeError, TimeoutError, KeyError, OSError) as e:
        print(f"[instagram] post failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
