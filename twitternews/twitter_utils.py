import os
import tweepy
from typing import Optional

def post_tweet(text: str) -> Optional[str]:
    """
    Post `text` to Twitter (X) using Tweepy's Client and credentials from environment.
    Returns tweet id string on success, None on failure.
    """
    TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        raise RuntimeError("Missing Twitter credentials. Ensure TWITTER_* vars are set in env or config.toml loaded into env.")

    try:
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
        )

        response = client.create_tweet(text=text)

        tweet_id = None
        if hasattr(response, "data") and response.data is not None:
            data = response.data
            if isinstance(data, dict):
                tweet_id = data.get("id")
            else:
                tweet_id = getattr(data, "id", None)

        if tweet_id:
            print("✅ Successfully posted a tweet!")
            print(f"Tweet ID: {tweet_id}")
            print(f"View Tweet: https://twitter.com/i/web/status/{tweet_id}")
            return str(tweet_id)
        else:
            print("❌ Post failed: No tweet id returned.")
            return None

    except tweepy.TweepyException as e:
        print(f"❌ An error occurred during the API call: {e}")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None
