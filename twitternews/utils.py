from urllib.parse import urlparse

RESTRICTED_DOMAINS = [
    "eltiempo.com",
    "noticiascaracol.com",
    "elespectador.com",
    "elcolombiano.com",
    "larepublica.co",
    "semana.com",
    "portafolio.co",
    "bluradio.com",
    "vanguardia.com",
    "elheraldo.co",
    "publimetro.co",
    "rcnradio.com",
    "caracol.com.co",
    "elpais.com.co",
    "lasillavacia.com",
    "dane.gov.co/index.php/actualidad-dane"
]

# Add specific URLs to this set to blacklist them exactly
BLACKLISTED_URLS = {
    "https://www.bluradio.com/noticias",
    "https://www.larepublica.co/videos/datos-cocteleros",
    "https://www.lafm.com.co/noticias/inversiones",
    "https://www.lafm.com.co/noticias/colombia,"
    "https://www.dane.gov.co/index.php/actualidad-dane",
    "https://www.larepublica.co/foros"
    
    # Add more URLs here as needed
}

BLACKLISTED_URL_PREFIXES = [
    "https://www.bluradio.com/noticias",
    "https://www.bluradio.com/casa-blu",
    "https://www.larepublica.co/indicadores-economicos",
    "https://www.elespectador.com/archivo",
    "https://caracol.com.co/tag",
    "https://www.elcolombiano.com/multimedia",
    "https://www.elheraldo.co/tags",
    "https://m.elcolombiano.com",
    "https://fincaraiz.elpais.com.co"
    # Add more URL prefixes here as needed
]

def is_blacklisted(url: str) -> bool:
    """
    True if URL is a root domain, a restricted domain with exactly one path segment,
    matches a specifically blacklisted URL, starts with a blacklisted prefix,
    or (for elcolombiano.com) contains '/meta/' in the path.
    """
    # Check for exact URL blacklist
    if url in BLACKLISTED_URLS:
        return True

    # Check for prefix blacklist (e.g., all subpages under a path)
    for prefix in BLACKLISTED_URL_PREFIXES:
        if url.startswith(prefix):
            return True

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        clean_path = parsed.path.strip("/")

        # Blacklist any elcolombiano.com URL containing '/meta/' in the path
        if "elcolombiano.com" in domain and "/meta/" in parsed.path:
            return True

        if not clean_path:
            return True

        if any(d in domain for d in RESTRICTED_DOMAINS):
            if len(clean_path.split("/")) == 1:
                return True

        # Blacklist URLs containing 'AMP' (case-insensitive)
        if "amp" in url.lower():
            return True

        return False
    except Exception:
        return False
