from curl_cffi import requests
from bs4 import BeautifulSoup
import json

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8,hi;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

s = requests.Session(impersonate="chrome110")
s.headers.update(headers)

def dump_amazon():
    url = "https://www.amazon.in/s?k=iphone+14"
    res = s.get(url)
    soup = BeautifulSoup(res.text, "lxml")
    
    divs = soup.select("div[data-component-type='s-search-result'][data-asin]")
    print(f"Amazon divs found: {len(divs)}")
    
    for div in divs[:2]:
        asin = div.get("data-asin", "")
        title_tag = div.select_one("h2 span")
        title = title_tag.get_text(strip=True) if title_tag else "No title"
        print(f"ASIN: {asin}, Title: {title}")
        
    with open("amazon_dump.html", "w") as f:
        f.write(res.text)

def dump_flipkart():
    url = "https://www.flipkart.com/search?q=iphone+14"
    res = s.get(url)
    soup = BeautifulSoup(res.text, "lxml")
    
    links = [a["href"] for a in soup.find_all("a", href=True) if "/p/" in a["href"] and "pid=" in a["href"]]
    print(f"Flipkart product links found: {len(links)}")
    
    if links:
        p_url = "https://www.flipkart.com" + links[0] if links[0].startswith("/") else links[0]
        res_p = s.get(p_url)
        p_soup = BeautifulSoup(res_p.text, "lxml")
        
        review_blocks = (
            p_soup.select("div.col.EPCmJX.Ma1fCG") or
            p_soup.select("div._27M-vq") or
            p_soup.select("div.t-ZTKy") or
            p_soup.select("div.row.feRevF") or
            p_soup.select("div[class*='review']")
        )
        print(f"Flipkart review blocks found: {len(review_blocks)}")
        with open("flipkart_dump.html", "w") as f:
            f.write(res_p.text)
            
if __name__ == "__main__":
    dump_amazon()
    dump_flipkart()
