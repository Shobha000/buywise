import asyncio
import logging
from backend.scrapers.amazon import AmazonScraper
from backend.scrapers.flipkart import FlipkartScraper

logging.basicConfig(level=logging.INFO)

async def test():
    amz = AmazonScraper()
    fk = FlipkartScraper()
    
    print("\n--- Testing Amazon ---")
    res_a = amz.search_and_scrape("iphone 14")
    print(f"Amazon result: available={res_a.available}, count={len(res_a.reviews) if res_a.available else 0}")
    
    print("\n--- Testing Flipkart ---")
    res_f = fk.search_and_scrape("iphone 14")
    print(f"Flipkart result: available={res_f.available}, count={len(res_f.reviews) if res_f.available else 0}")

if __name__ == "__main__":
    asyncio.run(test())
