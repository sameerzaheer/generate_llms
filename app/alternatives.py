import requests

def firecrawl_get(url_str):
    api_url = f"http://llmstxt.firecrawl.dev/{url_str}"
    response = requests.get(api_url)
    return response.text