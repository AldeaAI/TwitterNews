import re
import json
import requests
from perplexity import Perplexity
from .config import get_api_key
from typing import List

def generate_sources() -> str:
    """
    Generates a markdown list of Colombian news sources using the Perplexity API.
    Returns the raw markdown response.
    """
    api_key = get_api_key()
    client = Perplexity(api_key=api_key)
    prompt = (
        "Actúa como un experto en medios de comunicación de Colombia. Necesito una lista de 20 sitios web de noticias "
        "confiables y de alta reputación en el país. Por favor, incluye una mezcla de periódicos nacionales, "
        "revistas de negocios y portales de noticias financieras. Para cada sitio, proporciona el nombre y la "
        "URL principal (por ejemplo, El Tiempo - eltiempo.com). La lista debe estar formateada en markdown."
    )

    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="sonar",
    )
    return completion.choices[0].message.content

def validate_url(domain: str) -> bool:
    """
    Validates if a domain is active by making a HEAD request.
    """
    try:
        response = requests.head(f"http://{domain}", timeout=5, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

def extract_domains_from_markdown(markdown_list: str) -> List[str]:
    """
    Extract domains from a markdown bullet list (simple extraction).
    """
    return re.findall(r'-\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', markdown_list)

def generate_and_save(path: str = None) -> List[str]:
    """
    Generate sources via API, validate them and save to sources.json in project root.
    Returns the list of validated domains.
    """
    markdown_list = generate_sources()
    domains = extract_domains_from_markdown(markdown_list)
    valid = []
    for d in domains:
        if validate_url(d):
            valid.append(d)
    if path is None:
        path = "sources.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(valid, f, indent=4)
    return valid

if __name__ == "__main__":
    print("Generating news sources...")
    md = generate_sources()
    print(md)
    vals = generate_and_save()
    print(f"Saved {len(vals)} validated sources.")
