import asyncio
from backend.scrapers.amazon import AmazonScraper
from backend.scrapers.flipkart import FlipkartScraper
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    products = ["ordinary serum", "himalaya lip balm"]
    
    amz = AmazonScraper()
    fk = FlipkartScraper()
    amz.max_reviews = 10
    fk.max_reviews = 10
    
    for p in products:
        print(f"\n{'='*50}\nTesting '{p}'\n{'='*50}")
        
        print("\n--- Amazon ---")
        res_a = amz.safe_scrape(p)
        print(f"Available: {res_a.available}")
        for r in res_a.reviews[:3]:
            print(f"  [{r['rating']}★] {r['product']} - {r['text'][:60]}")
            
        print("\n--- Flipkart ---")
        res_f = fk.safe_scrape(p)
        print(f"Available: {res_f.available}")
        for r in res_f.reviews[:3]:
            print(f"  [{r['rating']}★] {r['product']} - {r['text'][:60]}")

if __name__ == "__main__":
    asyncio.run(test())
