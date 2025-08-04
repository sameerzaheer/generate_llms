import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import tldextract
from collections import deque
import math
from typing import List

class PageNode:
    def __init__(self, url, index):
        self.url = url
        self.title = None
        self.description = ""
        self.index = index
        self.children: List[PageNode] = []

    def update(self, title, description):
        self.title = title
        self.description = description

    def add_child(self, child_node):
        self.children.append(child_node)

    def print_tree(self):
        printed_tree=''
        node_stack = [(self, 0)]  # (node, indent_level)
        while node_stack:
            node, indent = node_stack.pop()
            prefix = "**" * indent
            printed_tree += (f"{prefix}- {node.url} -- {node.title}\n")
            # printed_tree += (f"{prefix}  Title: {node.title}")
            # printed_tree += (f"{prefix}  Index: {node.index}")
            # printed_tree += (f"{prefix}  Description: {node.description}")

            for child in node.children:
                if child.title is not None:
                    node_stack.append((child, indent + 1))
        return printed_tree
    
    def print_tree_as_markdown(self):
        printed_tree=''
        printed_tree+=(f"# {self.title}\n")
        printed_tree+=(f"> {self.description}\n")
        for child in self.children:
            if child.title is not None:
                printed_tree+=(f"## {child.title}\n")
                printed_tree+=(f"- [{child.title}]({child.url}): {child.description}\n")
                for grandkid in child.children:
                    if grandkid.title is not None:
                        printed_tree+=(f"- [{grandkid.title}]({grandkid.url}): {grandkid.description}\n")

        return printed_tree

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
    base_domain = tldextract.extract(base_url).top_domain_under_public_suffix
    target_domain = tldextract.extract(target_url).top_domain_under_public_suffix
    return base_domain == target_domain

def clean_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

def crawl_site_as_tree(root_url, max_pages=3, max_depth=5):
    cleaned_root = clean_url(root_url)
    root_domain = cleaned_root
    visited = set()
    queue = deque()

    root_node = PageNode(cleaned_root, index=0)
    queue.append((root_node, cleaned_root, 0))
    visited.add(cleaned_root)
    count = 0
    curr_depth_from_root = 0

    while queue and count < max_pages and curr_depth_from_root < max_depth:
        current_node, current_url, depth = queue.popleft()

        try:
            response = requests.get(current_url, timeout=5)
            if response.status_code != 200:
                continue
            if 'text/html' not in response.headers.get('Content-Type', ''):
                continue
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception:
            continue

        title = soup.title.string.strip() if soup.title else "No Title"
        texts = soup.get_text(separator=' ', strip=True)
        description = get_description(soup, texts)

        current_node.update(title, description)
        count += 1
        if count % 10 == 0:
            print(f"{count} / {max_pages} pages traversed")

        if curr_depth_from_root < max_depth:
            for link_tag in soup.find_all('a', href=True):
                href = link_tag['href']
                full_url = clean_url(urljoin(current_url, href))

                if full_url in visited or not is_same_domain(root_domain, full_url):
                    continue

                child_node = PageNode(full_url, index=depth + 1)
                current_node.add_child(child_node)
                queue.append((child_node, full_url, depth + 1))
                visited.add(full_url)

    return root_node

def tree_to_markdown_string(root_node):
    return root_node.print_tree_as_markdown()

def create_llms(url_str):
    rootnode = crawl_site_as_tree(url_str)
    markdown_str = tree_to_markdown_string(rootnode)
    return markdown_str

# app/crawler.py
from celery_worker import celery

@celery.task
def scheduled_crawl(url):
    print(f"Crawling {url} for updates...")
    llms_txt = "-0-" + url 
    #llms_txt = create_llms(url)  # Your existing function
    # Compare with old version, update db, notify, etc.
    return llms_txt


# Example usage:
if __name__ == "__main__":
    root = "https://www.tryprofound.com"
    print(create_llms(root))
