import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import tldextract
from collections import deque

def get_first_sentence(text):
    if not text:
        return ""
    sentences = text.strip().split('. ')
    if sentences:
        return sentences[0].strip().replace('\n', ' ') + ('.' if '.' not in sentences[0] else '')
    return ""

def get_description(soup, fallback_text):
    # Try to find meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    # Fallback to first sentence
    return get_first_sentence(fallback_text)


def is_same_domain(base_url, target_url):
    base_domain = tldextract.extract(base_url).registered_domain
    target_domain = tldextract.extract(target_url).registered_domain
    return base_domain == target_domain

def crawl_site(root_url, max_pages=30):
    visited = set()
    to_visit = deque([(root_url, 0)])
    result = {}

    while to_visit and len(visited) < max_pages:
        current_url, depth = to_visit.popleft()
        if current_url in visited:
            continue

        try:
            response = requests.get(current_url, timeout=5)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            continue

        title = soup.title.string.strip() if soup.title else "No Title"
        texts = soup.get_text(separator=' ', strip=True)
        description = get_description(soup, texts)

        result[current_url] = {
            "title": title,
            "index": depth,
            "first_sentence": description
        }

        visited.add(current_url)

        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href']
            full_url = urljoin(current_url, href)
            parsed_url = urlparse(full_url)
            cleaned_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

            if cleaned_url not in visited and is_same_domain(root_url, cleaned_url):
                to_visit.append((cleaned_url, depth + 1))

    return result

def dict_to_markdown_string(crawl_result):
    markdown_str=""
    for url, info in crawl_result.items():
        item_str = f"{url}:\n  Title: {info['title']}\n  Index: {info['index']}\n  First sentence: {info['first_sentence'][:80]}\n"
        markdown_str += item_str

def create_llms(url_str):
    crawl_result = crawl_site(url_str)
    markdown_str = dict_to_markdown_string(crawl_result)
    return markdown_str

# Example usage:
if __name__ == "__main__":
    root = "https://www.tryprofound.com"
    print(create_llms(root))
