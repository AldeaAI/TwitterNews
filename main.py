import os
import json
from datetime import datetime, timedelta
import difflib
import toml
from perplexity import Perplexity

def get_api_key():
    """
    Reads the Perplexity API key from environment variables or a local config.toml file.
    Priority is given to the environment variable.
    """
    # 1. Try environment variable (for GitHub Actions)
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if api_key:
        return api_key

    # 2. Try config.toml (for local development)
    try:
        with open("config.toml", "r") as f:
            config = toml.load(f)
        api_key = config.get("PERPLEXITY_API_KEY")
        if api_key and api_key != "YOUR_API_KEY_HERE":
            return api_key
    except FileNotFoundError:
        pass  # config.toml is optional

    # 3. If neither works, fail
    raise ValueError(
        "API key not found. Please set the PERPLEXITY_API_KEY environment variable "
        "or create a config.toml file with your key."
    )

def load_sources():
    """
    Loads the list of valid news sources from sources.json.
    """
    with open("sources.json", "r") as f:
        return json.load(f)

def load_history():
    """
    Loads the history of posted articles and purges entries older than a week.
    """
    try:
        with open("post_history.json", "r") as f:
            history = json.load(f)
    except FileNotFoundError:
        return []

    one_week_ago = datetime.now() - timedelta(days=7)
    
    # Filter out entries older than one week
    fresh_history = [
        item for item in history
        if datetime.fromisoformat(item["date"]) > one_week_ago
    ]
    
    if len(history) != len(fresh_history):
        print(f"Purged {len(history) - len(fresh_history)} old entries from history.")
        with open("post_history.json", "w") as f:
            json.dump(fresh_history, f, indent=4)
            
    return fresh_history

def save_history(url, history):
    """
    Saves the updated history of posted articles.
    """
    new_entry = {
        "url": url,
        "date": datetime.now().isoformat()
    }
    history.append(new_entry)
    with open("post_history.json", "w") as f:
        json.dump(history, f, indent=4)

def main():
    """
    Main function to run the agent pipeline.
    """
    print("Starting the Twitter post generation pipeline...")
    
    # Load configuration and history
    api_key = get_api_key()
    sources = load_sources()
    history = load_history()
    
    print(f"Loaded {len(sources)} news sources. Found {len(history)} articles in history.")
    
    # Step 1: News Research Agent
    print("\n[Agent 1/3] Searching for news...")
    found_articles = news_research_agent(api_key, sources)

    print("\n--- Found URLs ---")
    if found_articles:
        for article in found_articles:
            print(f"- {article.date}: {article.title} - {article.url}")
    else:
        print("No articles found.")
    print("------------------\n")
    
    # Filter out already posted articles
    history_urls = [item["url"] for item in history]
    articles = [article for article in found_articles if article.url not in history_urls]
    print(f"Found {len(found_articles)} total articles, {len(articles)} are new.")
    
    if not articles:
        print("No relevant articles found. Exiting.")
        return
        
    print(f"Found {len(articles)} potential articles.")
    
    
    # Step 2: Impact Analysis Agent
    print("\n[Agent 2/3] Analyzing articles for impact...")
    most_relevant_article = impact_analysis_agent(api_key, articles)
    
    if not most_relevant_article:
        print("Could not determine the most relevant article. Exiting.")
        return
        
    print(f"Most relevant article: '{most_relevant_article.title}'")
    
    # Step 3: Twitter Writer Agent
    print("\n[Agent 3/3] Generating Twitter post...")
    tweet = twitter_writer_agent(api_key, most_relevant_article)
    
    print("\n--- Generated Tweet ---")
    print(tweet)
    print("-----------------------\n")
    
    # Save the posted article to history
    save_history(most_relevant_article.url, history)
    print(f"Article '{most_relevant_article.title}' saved to history.")

def twitter_writer_agent(api_key, article):
    """
    Generates a Twitter post from the selected article.
    """
    client = Perplexity(api_key=api_key)
    
    prompt = (
        "Eres un analista de mercado experto en el sector inmobiliario. Tu tarea es redactar un post para Twitter "
        "resumiendo la siguiente noticia. El post debe tener un tono sobrio, inteligente y conciso. No utilices emojis "
        "ni signos de exclamación. El post debe:\n"
        "- Resumir el punto clave de la noticia (máximo 280 caracteres).\n"
        "- Incluir el hashtag #AldeaAI y otros 2-3 hashtags relevantes generados a partir del contenido del artículo.\n"
        "- Al final del post, añade la URL de la noticia original.\n\n"
        f"Noticia:\n"
        f"Título: {article.title}\n"
        f"Contenido: {article.snippet}\n"
        f"Fuente: {article.url}"
    )
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="sonar-pro",
    )
    
    return completion.choices[0].message.content

def impact_analysis_agent(api_key, articles):
    """
    Analyzes the found articles to select the most impactful one.
    """
    client = Perplexity(api_key=api_key)
    
    article_summaries = "\n".join([f"{i+1}. {article.title}: {article.snippet}" for i, article in enumerate(articles)])
    
    prompt = (
        "Eres un analista experto en el mercado inmobiliario de Colombia. A continuación se presenta una lista numerada de "
        "noticias recientes. Tu tarea es la siguiente:\n"
        "1. Analiza brevemente la relevancia de cada artículo para el mercado inmobiliario colombiano.\n"
        "2. Basado en tu análisis, y dando prioridad a noticias de Medellín si las hay, selecciona la noticia que consideres más interesante para una audiencia de personas interesadas en invertir en propiedad raíz.\n"
        "3. En una nueva línea, al final de toda tu respuesta, escribe ÚNICAMENTE el número del artículo que elegiste (ej: 3).\n\n"
        f"Artículos:\n{article_summaries}"
    )
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="sonar-pro",
    )
    
    full_response = completion.choices[0].message.content.strip()
    print("\n--- Analyst Agent's Reasoning ---")
    print(full_response)
    print("---------------------------------\n")

    # The final choice is the last line of the response
    # The final choice is the last line of the response
    try:
        selected_index = int(full_response.split('\n')[-1]) - 1
        if 0 <= selected_index < len(articles):
            return articles[selected_index]
    except (ValueError, IndexError):
        return None
                
    return None

def news_research_agent(api_key, sources):
    """
    Searches for recent news about the Colombian real estate market.
    """
    client = Perplexity(api_key=api_key)
    
    queries = [
        "noticias mercado inmobiliario Colombia",
        "inversión en vivienda Colombia",
        "tendencias sector construcción Colombia",
        "créditos hipotecarios Colombia",
        "precios de la vivienda en Colombia",
        "subsidios de vivienda Colombia",
        "mercado de oficinas en Colombia",
        "inversión en locales comerciales Colombia",
        "proyectos inmobiliarios en Medellín",
        "mercado inmobiliario de Miami para colombianos",
    ]
    
    all_results = []
    seen_urls = set()

    for query in queries:
        search = client.search.create(
            query=query,
            country="CO",
            search_language_filter=["es"],
            search_recency_filter="week",
            search_domain_filter=sources,
            max_results=10,
        )
        
        for result in search.results:
            if result.url not in seen_urls:
                all_results.append(result)
                seen_urls.add(result.url)
                
    return all_results

if __name__ == "__main__":
    main()