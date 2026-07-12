import requests

API_KEY = "N5r2oscYpyTlryw8xkuTwzH3adcrhSdd"

url = f"https://api.tomtom.com/search/2/geocode/Mangalore.json?key={API_KEY}"

try:
    r = requests.get(url, timeout=10)
    print("Status:", r.status_code)
    print(r.text)
except Exception as e:
    print(e)