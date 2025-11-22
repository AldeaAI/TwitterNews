from typing import List, Optional, Any
from perplexity import Perplexity
from .utils import is_blacklisted

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
            max_results=3,
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
    article_summaries = "\n".join(
        [f"{i+1}. {a.title}: {a.snippet}" for i, a in enumerate(articles)]
    )
    prompt = (
        "Eres un analista experto en el mercado inmobiliario de Colombia. A continuación se presenta una lista numerada de "
        "noticias recientes. Tu tarea es la siguiente:\n"
        "1. Analiza brevemente la relevancia de cada artículo para el mercado inmobiliario colombiano.\n"
        "2. Basado en tu análisis, y dando prioridad a noticias de Medellín si las hay, selecciona la noticia que consideres más interesante para una audiencia de personas interesadas en invertir en propiedad raíz y en el sector inmobiliario.\n"
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
    try:
        selected_index = int(full_response.split("\n")[-1]) - 1
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
    prompt = (
        "Eres un analista de mercado experto en el sector inmobiliario. Tu tarea es redactar un post para Twitter "
        "resumiendo la siguiente noticia. El post debe tener un tono sobrio, inteligente y conciso. No utilices emojis "
        "ni signos de exclamación. El post debe:\n"
        "- Resumir el punto clave de la noticia (máximo 260 caracteres).\n"
        "- Incluir el hashtag #AldeaAI.\n"
        "- Al final del post, añade la URL de la noticia original.\n\n"
        f"Noticia:\nTítulo: {article.title}\nContenido: {article.snippet}\nFuente: {article.url}"
    )
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="sonar-pro",
    )
    return completion.choices[0].message.content
