from typing import List, Optional, Any
from perplexity import Perplexity
from .utils import is_blacklisted
import json
import re

def news_research_agent(api_key: str, sources: List[str]) -> List[Any]:
    """
    Searches for recent news about the Colombian real estate market using Perplexity's search API.
    Filters out blacklisted URLs and deduplicates results.
    Returns a list of article objects (as returned by Perplexity).
    """
    client = Perplexity(api_key=api_key)
    queries = [
        "noticias mercado inmobiliario Colombia",
        "inversión en vivienda Colombia",
        # "tendencias sector construcción Colombia",
        # "créditos hipotecarios Colombia",
        # "precios de la vivienda en Colombia",
        # "subsidios de vivienda Colombia",
        # "mercado de oficinas en Colombia",
        # "inversión en locales comerciales Colombia",
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
            max_results=7,
        )
        for result in search.results:
            if result.url not in seen_urls and not is_blacklisted(result.url):
                all_results.append(result)
                seen_urls.add(result.url)
    return all_results

def impact_analysis_agent(api_key: str, articles: List[Any]) -> Optional[Any]:
    """
    Analyzes the found articles to select the most impactful one using Perplexity's chat API.
    Returns the selected article object or None.
    """
    if not articles:
        return None
    client = Perplexity(api_key=api_key)
    # Build a JSON array of article objects (id, title, snippet, url)
    article_list = [
        # {"id": i + 1, "title": a.title, "snippet": a.snippet, "url": a.url}
        {"id": i + 1, "title": a.title,  "url": a.url}
        for i, a in enumerate(articles)
    ]
    article_summaries = json.dumps(article_list, ensure_ascii=False, indent=2)
    prompt = (
        "Eres un analista experto en el mercado inmobiliario de Colombia. A continuación se presenta un array JSON con "
        "noticias. Cada elemento es un objeto con campos 'id', 'title' y 'url'.\n"
        "Tu tarea es la siguiente:\n"
        "1. Analiza brevemente la relevancia de cada artículo para el mercado inmobiliario colombiano.\n"
        "2. Basado en tu análisis, y dando prioridad a noticias de Medellín si las hay, selecciona la noticia que consideres más interesante para una audiencia de personas interesadas en invertir en propiedad raíz y en el sector inmobiliario.\n"
        "3. En una nueva línea, al final de toda tu respuesta, escribe SOLO el 'id' del artículo que elegiste (ej: 3).\n\n"
        f"Artículos (JSON):\n{article_summaries}"
    )
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="sonar",
    )
    full_response = completion.choices[0].message.content.strip()
    print("\n--- Analyst Agent's Reasoning ---")
    print(full_response)
    print("---------------------------------\n")
    try:
        last_line = full_response.split("\n")[-1]
        selected_index = int(re.search(r'\d+', last_line).group(0)) -1 
        if 0 <= selected_index < len(articles):
            return articles[selected_index]
    except (ValueError, IndexError):
        return None
    return None

def twitter_writer_agent(api_key: str, article: Any) -> str:
    """
    Generates a Twitter post from the selected article using Perplexity's chat API.
    Returns the generated tweet text.
    """
    client = Perplexity(api_key=api_key)
    system_prompt = (
        "Eres un analista de mercado experto en el sector inmobiliario. "
        "Tu tarea es redactar un post para Twitter resumiendo la noticia proporcionada por el usuario. "
        "El post debe tener un tono sobrio, inteligente y conciso. No utilices emojis ni signos de exclamación. "
        "El post debe resumir el punto clave de la noticia y NO puede exceder los 245 caracteres, incluyendo espacios. Es obligatorio que tenga menos de 245 caracteres."
        "No incluyas ninguna información adicional. No menciones el número de caracteres en el post. No incluyas referencias ni numeros de citaciones."
    )

    user_prompt = (
        "Redacta el post de Twitter (tuit) utilizando la siguiente información de la noticia:\n\n"
        f"Noticia:\n"
        f"Título: {article.title}\n"
        f"Contenido: {article.snippet}\n"
        f"Fuente: {article.url}"
    )

    completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                    ], 
                model="sonar",

    )
    return completion.choices[0].message.content

def tweet_optimizer_agent(api_key: str, tweet_text: str) -> str:
    """
    Takes a tweet that exceeds 245 characters and optimizes it to be under 245 characters.
    Returns the optimized tweet text.
    """
    if len(tweet_text) <= 245:
        return tweet_text
    
    client = Perplexity(api_key=api_key)

    user_prompt = (
        f"Optimiza el siguiente tweet para que tenga menos de 245 caracteres. Solo escribe el nuevo tweet. Sin citaciones ni informacion adicional:\n\n"
        f"Tweet original ({len(tweet_text)} caracteres):\n{tweet_text}"
    )

    completion = client.chat.completions.create(
        messages=[
            {"role": "user", "content": user_prompt}
        ], 
        model="sonar",
    )
    
    optimized_tweet = completion.choices[0].message.content.strip()


    # Remove reference citations like [1], [2], etc. from the tweet
    optimized_tweet = re.sub(r'\[\d+\]', '', optimized_tweet).strip()

    # Remove "(number caracteres)" text if present
    optimized_tweet = re.sub(r'\(\d+\s+caracteres?\)', '', optimized_tweet).strip()

    return optimized_tweet