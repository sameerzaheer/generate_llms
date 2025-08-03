import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque

def crawl(start_url, max_pages=100):
    visited = set()
    queue = deque([start_url])
    site_map = {}

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = [urljoin(url, a.get('href')) for a in soup.find_all('a', href=True)]
            links = [l for l in links if urlparse(l).netloc == urlparse(start_url).netloc]
            site_map[url] = links
            queue.extend([l for l in links if l not in visited])
            visited.add(url)
        except:
            continue
    return site_map

print(crawl('https://www.tryprofound.com/',10))
