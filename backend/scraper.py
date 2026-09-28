import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

async def scrape_url(start_url: str, max_pages: int = 20):
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
                    
                text_content = soup.get_text(separator=' ', strip=True)
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
                
    return results

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
