import httpx
import re
from collections.abc import Awaitable, Callable
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def extract_link_references(soup: BeautifulSoup, page_url: str) -> list[str]:
    references = []
    seen_urls = set()
    for link in soup.find_all('a', href=True):
        label = link.get_text(' ', strip=True)
        target_url = urljoin(page_url, link['href'])
        if not label or target_url in seen_urls or urlparse(target_url).scheme not in {'http', 'https'}:
            continue
        seen_urls.add(target_url)
        references.append(f"- {label[:100]}: {target_url}")
        if len(references) >= 40:
            break
    return references


async def scrape_url(
    start_url: str,
    max_pages: int = 20,
    progress_callback: Callable[[int], Awaitable[None]] | None = None,
):
    visited = set()
    to_visit = [start_url]
    results = []
    
    base_domain = urlparse(start_url).netloc

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            
            visited.add(url)
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else url
                
                # Strip unwanted tags
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                    
                link_references = extract_link_references(soup, url)

                text_content = soup.get_text(separator=' ', strip=True)
                if link_references:
                    text_content += "\n\nWebsite links:\n" + "\n".join(link_references)
                if text_content:
                    results.append({
                        "url": url,
                        "title": title.strip(),
                        "content": text_content
                    })
                
                # Find links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(url, href)
                    # Only follow same domain
                    if urlparse(full_url).netloc == base_domain:
                        clean_url = full_url.split('#')[0]
                        if clean_url not in visited and clean_url not in to_visit:
                            to_visit.append(clean_url)
                            
            except Exception as e:
                print(f"Error scraping {url}: {e}")

            if progress_callback:
                await progress_callback(len(results))
                
    return results

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    link_pattern = re.compile(r"^\s*-\s+.{2,100}:\s+https?://\S+", re.IGNORECASE)
    content_lines = []
    link_chunks = []
    for line in text.splitlines():
        if link_pattern.match(line):
            link_chunks.append(line.strip())
        else:
            content_lines.append(line)

    words = "\n".join(content_lines).split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks + link_chunks
