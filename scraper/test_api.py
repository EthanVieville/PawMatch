# test_api.py

import requests

url = "https://www.la-spa.fr/app/wp-json/spa/v1/animals"

params = {
    "api": 1,
    "page": 1,
    "per_page": 10
}

res = requests.get(url, params=params)

print(res.status_code)
print(res.json())