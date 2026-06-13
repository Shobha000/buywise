from curl_cffi import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

def test():
    print("Testing Amazon with curl_cffi (impersonate Chrome)...")
    res_a = requests.get("https://www.amazon.in/s?k=iphone+14", impersonate="chrome110", headers=headers)
    print(f"Amazon status: {res_a.status_code}, length: {len(res_a.text)}")
    print(f"Contains sign-in? {'sign-in' in res_a.text.lower()}")
    print(f"Contains captcha? {'captcha' in res_a.text.lower()}")
    
    print("\nTesting Flipkart with curl_cffi (impersonate Chrome)...")
    res_f = requests.get("https://www.flipkart.com/search?q=iphone+14", impersonate="chrome110", headers=headers, timeout=15)
    print(f"Flipkart status: {res_f.status_code}, length: {len(res_f.text)}")
    print(f"Contains login? {'login' in res_f.text.lower()}")

if __name__ == "__main__":
    test()
