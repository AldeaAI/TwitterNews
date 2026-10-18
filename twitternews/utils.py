from urllib.parse import urlparse

# Tweet length: the writer and optimizer aim for TARGET characters (kept short on purpose),
# but a tweet up to MAX characters is still accepted, since X's standard limit is 280.
TWEET_TARGET_CHARS = 245
TWEET_MAX_CHARS = 280

# Display names for the source hashtag, keyed by the domain's main label (no www, no TLD)
SOURCE_NAMES = {
    "elcolombiano": "ElColombiano",
    "elespectador": "ElEspectador",
    "eltiempo": "ElTiempo",
    "larepublica": "LaRepublica",
    "portafolio": "Portafolio",
    "semana": "Semana",
    "bluradio": "BluRadio",
    "valoraanalitik": "ValoraAnalitik",
    "noticiascaracol": "NoticiasCaracol",
    "caracol": "Caracol",
    "vanguardia": "Vanguardia",
    "elheraldo": "ElHeraldo",
    "publimetro": "Publimetro",
    "rcnradio": "RCNRadio",
    "elpais": "ElPais",
    "forbes": "Forbes",
    "wradio": "WRadio",
    "lafm": "LaFM",
}


def source_hashtag(url: str) -> str:
    """
    Hashtag with the newspaper name for an article URL, e.g. '#ElColombiano'.
    Hashtags can't contain spaces, so names are written in CamelCase.
    Unknown sites fall back to their domain's main label, capitalized.
    """
    host = urlparse(url).netloc.lower().split(":")[0]
    labels = [part for part in host.split(".") if part != "www"]
    # Names like 'example.com.co' keep the name before the second-level suffix
    if len(labels) >= 3 and labels[-2] in ("com", "co", "org", "net", "gov"):
        main = labels[-3]
    elif len(labels) >= 2:
        main = labels[-2]
    else:
        main = host
    name = SOURCE_NAMES.get(main, main.capitalize())
    return f"#{name}"

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
