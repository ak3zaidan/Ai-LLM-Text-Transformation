import requests

url = "http://localhost:8080/jig"

data = {
    "address": "14955 SW Sophia LN",
    "count": 5
}

response = requests.post(url, json=data)

if response.ok:
    result = response.json()
    print("Jigged addresses:")
    for addr in result.get("jigs", []):
        print(f"- {addr}")
else:
    print(f"Error {response.status_code}: {response.text}")
