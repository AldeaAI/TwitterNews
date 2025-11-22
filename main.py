import sys
from twitternews.config import get_api_key, get_twitter_credentials, load_sources
from twitternews.history import load_history, save_history
from twitternews.agents import news_research_agent, impact_analysis_agent, twitter_writer_agent
from twitternews.twitter_utils import post_tweet

def main():
    print("Starting the Twitter post generation pipeline...")

    api_key = get_api_key()
    twitter_creds = get_twitter_credentials()
    print(f"hola {twitter_creds} ")
    if len(twitter_creds) < 4:
        print("Some Twitter credentials are missing. Posting may fail if required credentials are not provided.")
    else:
        print("Twitter credentials loaded.")

    # sources = load_sources()
    # history = load_history()

    # print(f"Loaded {len(sources)} news sources. Found {len(history)} articles in history.")

    # print("\n[Agent 1/3] Searching for news...")
    # found_articles = news_research_agent(api_key, sources)

    # print("\n--- Found URLs ---")
    # if found_articles:
    #     for article in found_articles:
    #         print(f"- {getattr(article, 'date', '')}: {article.title} - {article.url}")
    # else:
    #     print("No articles found.")
    # print("------------------\n")

    # history_urls = [item["url"] for item in history]
    # articles = [a for a in found_articles if a.url not in history_urls]
    # print(f"Found {len(found_articles)} total articles, {len(articles)} are new.")

    # if not articles:
    #     print("No relevant articles found. Exiting.")
    #     return

    # print("\n[Agent 2/3] Analyzing articles for impact...")
    # most_relevant = impact_analysis_agent(api_key, articles)
    # if not most_relevant:
    #     print("Could not determine the most relevant article. Exiting.")
    #     return

    # print(f"Most relevant article: '{most_relevant.title}'")

    # print("\n[Agent 3/3] Generating Twitter post...")
    # tweet = twitter_writer_agent(api_key, most_relevant)

    # print("\n--- Generated Tweet ---")
    # print(tweet)
    # print("-----------------------\n")

    # try:
    #     posted_id = post_tweet(tweet)
    #     if posted_id:
    #         print(f"Posted tweet id: {posted_id}")
    #     else:
    #         print("Tweet was not posted.")
    # except Exception as e:
    #     print(f"Failed to post tweet: {e}")

    # save_history(most_relevant.url, history)
    # print(f"Article '{most_relevant.title}' saved to history.")

    posted_id = post_tweet("Hello, world! This is a test tweet from the TwitterNews bot. #AldeaAI")

if __name__ == "__main__":
    main()