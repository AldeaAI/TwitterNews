import os
import re
import json
import toml
import requests
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

def generate_sources():
    """
    Generates a list of Colombian news sources using the Perplexity API.
    """
    api_key = get_api_key()
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise ValueError("Please set your Perplexity API key in config.toml")
    
    client = Perplexity(api_key=api_key)
    prompt = (
        "Actúa como un experto en medios de comunicación de Colombia. Necesito una lista de 20 sitios web de noticias "
        "confiables y de alta reputación en el país. Por favor, incluye una mezcla de periódicos nacionales, "
        "revistas de negocios y portales de noticias financieras. Para cada sitio, proporciona el nombre y la "
        "URL principal (por ejemplo, El Tiempo - eltiempo.com). La lista debe estar formateada en markdown."
    )

    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="sonar-pro",
    )
    return completion.choices[0].message.content

def validate_url(url):
    """
    Validates if a URL is active by making a HEAD request.
    """
    try:
        response = requests.head(f"http://{url}", timeout=5, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

def main():
    """
    Main function to generate, validate, and save news sources.
    """
    print("Generating news sources...")
    markdown_list = generate_sources()

    print("\n--- API Response ---")
    print(markdown_list)
    print("--------------------\n")

    # Extract URLs from the markdown list
    urls = re.findall(r'-\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', markdown_list)
    
    valid_sources = []
    print("Validating URLs...")
    for domain in urls:
        if validate_url(domain):
            print(f"  [OK] {domain}")
            valid_sources.append(domain)
        else:
            print(f"  [FAIL] {domain}")

    with open("sources.json", "w") as f:
        json.dump(valid_sources, f, indent=4)

    print(f"\nSaved {len(valid_sources)} valid sources to sources.json")

if __name__ == "__main__":
    main()