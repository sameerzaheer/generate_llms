import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import tldextract
import hashlib
import re
from collections import deque
import math
from typing import List
from datetime import datetime, date, timedelta

MAX_PAGES = 100
MAX_DEPTH = 5

class PageNode:
    def __init__(self, url, index):
        self.url = url
        self.title = None
        self.description = ""
        self.index = index
        self.children: List[PageNode] = []
        self.content_hash = None

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

import hashlib
import re
from bs4 import BeautifulSoup

def clean_html_for_hashing(soup, debug=False):
    """
    Clean HTML content by removing dynamic/volatile elements before hashing.
    Returns cleaned HTML string ready for hashing.
    """
    # Make a copy to avoid modifying the original
    cleaned_soup = BeautifulSoup(str(soup), 'html.parser')
    
    # Remove script and style tags entirely
    for tag in cleaned_soup(['script', 'style', 'noscript']):
        tag.decompose()
    
    # Remove meta tags (often contain timestamps, cache info, etc.)
    for tag in cleaned_soup.find_all('meta'):
        tag.decompose()
    
    # Remove common dynamic elements - expanded list
    dynamic_selectors = [
        # Time-based elements
        '[data-timestamp]', '[data-time]', '[data-date]',
        '.timestamp', '.date-updated', '.last-modified', '.time',
        
        # Session and tracking
        '[data-session]', '[data-csrf]', '[data-token]', '[data-nonce]',
        '.csrf-token', '[name="csrf-token"]', '[name="_token"]',
        
        # Analytics and ads
        '[data-ga]', '[data-gtm]', '[data-analytics]', '[data-track]',
        '.google-ads', '.advertisement', '.ad-banner', '.tracking-pixel',
        '[data-ad]', '.ads', '.adsense',
        
        # Social media widgets
        '.facebook-like', '.twitter-tweet', '.instagram-media',
        '.social-widget', '[data-social]',
        
        # Comments and dynamic content
        '#comments', '.comments-section', '.disqus-thread',
        '.comment-count', '.comment-form',
        
        # Live counters and stats
        '.view-count', '.visitor-count', '.online-users',
        '.counter', '.stat-number', '[data-count]',
        
        # Forms with dynamic tokens
        'input[name="csrf-token"]', 'input[name="_token"]',
        'input[type="hidden"][name*="token"]',
        
        # Random/dynamic IDs
        '[id*="random"]', '[id*="temp"]', '[class*="random"]',
        '[class*="temp"]', '[data-random]'
    ]
    
    # Remove elements matching dynamic selectors
    for selector in dynamic_selectors:
        for element in cleaned_soup.select(selector):
            element.decompose()
    
    # Remove ALL attributes except the most essential ones
    # This is aggressive but eliminates most dynamic content
    keep_attrs = {'href', 'src', 'alt', 'title'}  # Only keep truly content-related attributes
    
    for tag in cleaned_soup.find_all():
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr not in keep_attrs:
                attrs_to_remove.append(attr)
        
        for attr in attrs_to_remove:
            del tag.attrs[attr]
    
    # Remove form elements entirely (they often have dynamic tokens)
    for tag in cleaned_soup(['form', 'input', 'textarea', 'select', 'button']):
        tag.decompose()
    
    # Get the cleaned HTML text
    html_text = str(cleaned_soup)
    
    # More aggressive text normalization
    # Remove all newlines and normalize whitespace
    html_text = re.sub(r'\s+', ' ', html_text)
    html_text = re.sub(r'>\s+<', '><', html_text)
    
    # Remove HTML comments
    html_text = re.sub(r'<!--.*?-->', '', html_text, flags=re.DOTALL)
    
    # Remove common dynamic patterns in text
    # Remove timestamps, dates, session IDs
    html_text = re.sub(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[Z\+\-\d:]*\b', '', html_text)  # ISO dates
    html_text = re.sub(r'\b[a-f0-9]{32,}\b', '', html_text, re.I)  # Long hex strings (hashes, tokens)
    html_text = re.sub(r'\b[A-Za-z0-9]{20,}\b', '', html_text)  # Long random strings
    
    # Strip leading/trailing whitespace
    html_text = html_text.strip()
    
    if debug:
        print(f"Cleaned HTML length: {len(html_text)}")
        print(f"First 500 chars: {html_text[:500]}")
    
    return html_text

def generate_content_hash(cleaned_html):
    """Generate SHA-256 hash of cleaned HTML content."""
    return hashlib.sha256(cleaned_html.encode('utf-8')).hexdigest()

def debug_content_differences(url):
    """
    Helper function to debug what's changing between requests.
    Run this to see what content is different between two requests.
    """
    
    print("Fetching first version...")
    response1 = requests.get(url, timeout=5)
    soup1 = BeautifulSoup(response1.text, 'html.parser')
    clean1 = clean_html_for_hashing(soup1, debug=True)
    hash1 = generate_content_hash(clean1)
    
    print(f"\nFirst hash: {hash1}")
    
    print("\nWaiting 2 seconds...")
    import time
    time.sleep(2)
    
    print("Fetching second version...")
    response2 = requests.get(url, timeout=5)
    soup2 = BeautifulSoup(response2.text, 'html.parser')
    clean2 = clean_html_for_hashing(soup2, debug=True)
    hash2 = generate_content_hash(clean2)
    
    print(f"\nSecond hash: {hash2}")
    
    if hash1 != hash2:
        print("\n❌ HASHES ARE DIFFERENT!")
        
        # Save both versions to files for manual inspection
        with open('version1.html', 'w', encoding='utf-8') as f:
            f.write(clean1)
        with open('version2.html', 'w', encoding='utf-8') as f:
            f.write(clean2)
        
        print("Saved cleaned versions to version1.html and version2.html")
        print("You can diff these files to see what's changing")
        
        # Show a simple character-by-character diff
        min_len = min(len(clean1), len(clean2))
        for i in range(min_len):
            if clean1[i] != clean2[i]:
                print(f"First difference at position {i}:")
                print(f"  Version 1: '{clean1[max(0,i-20):i+20]}'")
                print(f"  Version 2: '{clean2[max(0,i-20):i+20]}'")
                break
    else:
        print("\n✅ Hashes are the same!")

# Test the debugging function:
# debug_content_differences(current_url)

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

def crawl_site_as_tree(root_url, max_pages=MAX_PAGES, max_depth=MAX_DEPTH):
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
        content_hash = generate_content_hash(clean_html_for_hashing(soup))
        if content_hash == current_node.content_hash:
            continue
        current_node.content_hash = content_hash

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
    print("creating llms for ", url_str, " at time ", datetime.now())
    rootnode = crawl_site_as_tree(url_str)
    markdown_str = tree_to_markdown_string(rootnode)
    return markdown_str

# Example usage:
if __name__ == "__main__":
    root = "https://www.tryprofound.com"
    print(create_llms(root))
