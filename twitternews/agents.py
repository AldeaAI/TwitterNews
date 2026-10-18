from typing import List, Optional, Any, Tuple
from dataclasses import dataclass
from perplexity import Perplexity
from .utils import is_blacklisted, TWEET_TARGET_CHARS
import json
import re

# The Perplexity SDK changed how it deserializes responses: older versions returned
# nested pydantic models, newer ones (>= ~0.4x) leave nested objects as plain dicts.
# These helpers read either shape so the agents work on any installed version.

def _field(obj: Any, name: str, default: Any = "") -> Any:
    """Read `name` from a dict or an object, falling back to `default`."""
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return default if value is None else value

@dataclass
class Article:
    """Normalized search result, independent of the SDK response shape."""
    title: str
    url: str
    snippet: str = ""
    date: str = ""

def _to_article(result: Any) -> Optional[Article]:
    url = _field(result, "url")
    if not url:
        return None
    return Article(
        title=_field(result, "title"),
        url=url,
        snippet=_field(result, "snippet"),
        date=_field(result, "date"),
    )

def _completion_text(completion: Any) -> str:
    """Extract the assistant message text from a chat completion response."""
    choices = _field(completion, "choices", [])
    if not choices:
        return ""
    message = _field(choices[0], "message", {})
    return str(_field(message, "content", "")).strip()

def news_research_agent(api_key: str, sources: List[str]) -> List[Article]:
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
        for result in _field(search, "results", []):
            article = _to_article(result)
            if article is None:
                continue
            if article.url not in seen_urls and not is_blacklisted(article.url):
                all_results.append(article)
                seen_urls.add(article.url)
    return all_results

def impact_analysis_agent(api_key: str, articles: List[Article]) -> Optional[Article]:
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
    full_response = _completion_text(completion)
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

TWEET_SHORT_MAX_CHARS = 90

def _clean_text(text: str) -> str:
    """Remove citations, '(N caracteres)' leftovers and surrounding quotes from model output."""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\(\d+\s+caracteres?\)', '', text)
    text = re.sub(r'\[\d+\s+caracteres?\]', '', text)
    text = re.sub(r'\s+([.,;:])', r'\1', text)
    return text.strip().strip('"').strip()

def post_copy_agent(api_key: str, article: Article) -> Tuple[str, str]:
    """
    One LLM call that writes both texts for the daily post:
      - tweet: short tweet text (max 90 characters)
      - image: the longer summary printed on the post image (aims for 245 characters)
    Returns (tweet, image_text). Falls back to the article title and snippet when the answer
    cannot be parsed.
    """
    client = Perplexity(api_key=api_key)
    system_prompt = (
        "Eres un analista de mercado experto en el sector inmobiliario. "
        "A partir de la noticia del usuario redacta dos textos en español, con tono sobrio, inteligente y conciso. "
        "No utilices emojis ni signos de exclamación. "
        f"\"tweet\": un titular corto para el tweet, de máximo {TWEET_SHORT_MAX_CHARS} caracteres, incluyendo espacios. "
        f"\"imagen\": un resumen del punto clave de la noticia, que irá sobre la imagen, de menos de {TWEET_TARGET_CHARS} caracteres, incluyendo espacios. "
        "Responde solo con un objeto JSON con las claves \"tweet\" e \"imagen\". "
        "No incluyas citaciones, números entre corchetes, ni información adicional, ni menciones el número de caracteres."
    )
    user_prompt = (
        "Redacta los textos a partir de la siguiente noticia:\n\n"
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
    raw = _completion_text(completion)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}

    tweet = _clean_text(str(data.get("tweet", "") or ""))
    image_text = _clean_text(str(data.get("imagen", "") or ""))

    if not tweet or len(tweet) > TWEET_SHORT_MAX_CHARS:
        print(f"[post_copy_agent] tweet unusable ({len(tweet)} chars), using article title")
        tweet = _clean_text(article.title)
        if len(tweet) > TWEET_SHORT_MAX_CHARS:
            tweet = tweet[:TWEET_SHORT_MAX_CHARS].rsplit(" ", 1)[0]
    if not image_text:
        print("[post_copy_agent] image text empty, using article snippet")
        image_text = _clean_text(article.snippet) or _clean_text(article.title)
    return tweet, image_text

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
    
    optimized_tweet = _completion_text(completion)


    # Remove reference citations like [1], [2], etc. from the tweet
    optimized_tweet = re.sub(r'\[\d+\]', '', optimized_tweet).strip()

    # Remove "(number caracteres)" text if present
    optimized_tweet = re.sub(r'\(\d+\s+caracteres?\)', '', optimized_tweet).strip()

    return optimized_tweet