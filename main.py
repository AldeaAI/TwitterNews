"""
TwitterNews Main Orchestrator

This script orchestrates a 3-agent pipeline to:
  1. Search news for Colombian real estate articles (news_research_agent)
  2. Analyze impact and select the most relevant article (impact_analysis_agent)
  3. Generate a Twitter post for the selected article (twitter_writer_agent)
  4. Optionally post the generated tweet to Twitter (post_tweet)
  5. Save the posted article to history

Environment / Config:
 - PERPLEXITY_API_KEY (required): API key for Perplexity
 - TWITTER_API_KEY / TWITTER_API_SECRET / TWITTER_ACCESS_TOKEN / TWITTER_ACCESS_TOKEN_SECRET
    (recommended) for posting via Tweepy. CI workflows (GitHub Actions) should set these as secrets.
 - PERPLEXITY_MODEL: Optional model name for Perplexity (e.g., "raptor-mini-preview")

Usage:
 - Locally: ensure config.toml contains keys or use environment variables.
 - In CI: provide secrets in the workflow YAML (see .github/workflows).
"""

# --- Imports (high-level) ---
# - twitternews.config: env/config helpers & source list loader
# - twitternews.history: history persistence (load/save)
# - twitternews.agents: Perplexity-powered agents (news, analysis, writer)
# - twitternews.twitter_utils: posting implementation that reads TWITTER_* from environment
import sys
from twitternews.config import get_api_key, get_twitter_credentials, load_sources
from twitternews.history import load_history, save_history
from twitternews.agents import news_research_agent, impact_analysis_agent, twitter_writer_agent, tweet_optimizer_agent
from twitternews.twitter_utils import post_tweet
import re

def main():
    """
    Main orchestrator: runs the pipeline and handles I/O.

    Sections:
      1. Startup & Configuration: load API keys, Twitter credentials, and configuration.
      2. Data Loading: load sources.json and post_history.json
      3. Agent Pipeline:
           - Agent 1: Call news_research_agent to find candidate articles
           - Agent 2: Call impact_analysis_agent to pick most relevant article
           - Agent 3: Call twitter_writer_agent to generate the tweet text
      4. Posting (optional): post_tweet to Twitter (requires TWITTER_* env keys)
      5. History: persist the posted article to avoid reposting
    """

    # -------------------------------
    # --- Startup & Configuration ---
    # -------------------------------

    # Print startup message for visibility in CI logs
    print("Starting the Twitter post generation pipeline...")

    # Perplexity API key - required
    # Will attempt to read PERPLEXITY_API_KEY env var or config.toml
    api_key = get_api_key()

    # Load Twitter credentials: prefer environment, fallback to config.toml
    # These will be exported to os.environ by get_twitter_credentials() if found in config.
    twitter_creds = get_twitter_credentials()
    if len(twitter_creds) < 4:
        # Informative warning: posting may fail if not provided
        # This is not fatal: the pipeline can still run to generate content
        print("Some Twitter credentials are missing. Posting may fail if required credentials are not provided.")
    else:
        print("Twitter credentials loaded.")


    # -------------------------------
    # --- Data Loading ---
    # -------------------------------

    # Load valid sources to search and the existing history of posted URLs
    sources = load_sources()
    history = load_history()

    print(f"Loaded {len(sources)} news sources. Found {len(history)} articles in history.")


    # -------------------------------
    # --- Agent 1: News Research Agent ---
    # -------------------------------

    print("\n[Agent 1/3] Searching for news...")
    found_articles = news_research_agent(api_key, sources)

    # Report results of agent 1
    print("\n--- Found URLs ---")
    if found_articles:
        for article in found_articles:
            # Use getattr for 'date' because search results may not always include it
            print(f"- {getattr(article, 'date', '')}: {article.title} - {article.url}")
    else:
        print("No articles found.")
    print("------------------\n")

    # Filter articles already posted in the last week (history)
    history_urls = [item["url"] for item in history]
    articles = [a for a in found_articles if a.url not in history_urls]
    print(f"Found {len(found_articles)} total articles, {len(articles)} are new.")

    if not articles:
        # If there's nothing new, stop early
        print("No relevant articles found. Exiting.")
        return

    # print(f"\n\nDEBUG\n {found_articles} \n")

    
    # -------------------------------
    # --- Agent 2: Impact Analysis Agent ---
    # -------------------------------

    # Select the most impactful article for the target audience
    print("\n[Agent 2/3] Analyzing articles for impact...")
    most_relevant = impact_analysis_agent(api_key, articles)
    if not most_relevant:
        print("Could not determine the most relevant article. Exiting.")
        return

    print(f"Most relevant article: '{most_relevant.title}'")


    # -------------------------------
    # --- Agent 3: Twitter Writer Agent ---
    # -------------------------------

    # Generate a concise Twitter post recommended for X (Twitter)
    print("\n[Agent 3/3] Generating Twitter post...")
    tweet = twitter_writer_agent(api_key, most_relevant)
    print("-----------------------\n")


    print("\n--- Generated Tweet Text ---")
    print(tweet)
    # print("-----------------------\n")

    # -------------------------------
    # --- Verify tweet length ---
    # -------------------------------

    # Remove reference citations like [1], [2], etc. from the tweet
    tweet = re.sub(r'\[\d+\]', '', tweet).strip()
    print("\n--- Tweet Text After Removing Citations ---")
    print(tweet)
    print("-----------------------\n")

    # Remove "(number caracteres)" or "[number caracteres]" text if present
    tweet = re.sub(r'\(\d+\s+caracteres?\)', '', tweet).strip()
    tweet = re.sub(r'\[\d+\s+caracteres?\]', '', tweet).strip()
  
    print("\n--- Tweet Text After Removing Character Count ---")
    print(tweet)
    print("-----------------------\n")

    # Check if tweet exceeds 245 characters (including spaces)
    if len(tweet) > 245:
        print(f"Warning: Tweet is {len(tweet)} characters, exceeds 245 character limit.")
        print("Attempting to optimize tweet to fit within limit...")

        tweet = tweet_optimizer_agent(api_key, tweet)
        
        print("optimised tweet length:", len(tweet))

        print("\n--- Optimized Tweet Text ---")
        print(tweet)
        print("-----------------------\n")

        if len(tweet) > 245:
            print(f"Error: Optimized tweet is still {len(tweet)} characters, exceeds 245 character limit.")
            print("Cannot proceed with posting. Please review the optimization logic.")
            return
        # print("Consider regenerating or manually shortening the tweet.")
        # return
    else:
        print(f"Tweet length: {len(tweet)} characters (within 245 character limit)")
    # -------------------------------
    # --- Add hashtag to tweet ---
    # -------------------------------

    # Add #AldeaAI hashtag to the tweet
    if "#AldeaAI" not in tweet:
        # Check if adding hashtag would exceed character limit
        tweet_with_hashtag = f"{tweet} #AldeaAI"
        tweet = tweet_with_hashtag
        print(f"Added #AldeaAI hashtag. New tweet length: {len(tweet)} characters\n")


    # -------------------------------
    # --- Add website source to tweet ---
    # -------------------------------
    
    # Add the source website URL to provide attribution
    if most_relevant.url:
        # Extract domain from URL for cleaner display
        domain = most_relevant.url
        
        # Create attribution text
        source_text = f" {domain}"
        
        # Check if adding source would exceed character limit
        tweet_with_source = f"{tweet}{source_text}"
        tweet = tweet_with_source
        print(f"Added source attribution. New tweet length: {len(tweet_with_hashtag) + 23} characters")


    print("\n--- Generated Full Tweet Text ---")
    print(tweet)
    print("-----------------------\n")

    # -------------------------------
    # --- Optional: Posting the tweet ---
    # -------------------------------

    # The following code posts the generated tweet to Twitter using credentials from the environment.
    # It is currently enabled on main when valid TWITTER_* credentials are present. If you prefer to
    # TEST LOCALLY without posting, comment out the call to post_tweet or remove the TWITTER_* env entries.
    try:
        posted_id = post_tweet(tweet)
        if posted_id:
            print(f"Posted tweet id: {posted_id}")
        else:
            print("Tweet was not posted.")
    except Exception as e:
        # Be explicit about failures: often indicates permissions (403) or invalid credentials
        print(f"Failed to post tweet: {e}")

    # --- History: Persist the posted URL ---
    # Save the article to the history so it is not posted again in the short term
    save_history(most_relevant.url, history)
    print(f"\nArticle '{most_relevant.title}' saved to history.")


if __name__ == "__main__":
    main()
