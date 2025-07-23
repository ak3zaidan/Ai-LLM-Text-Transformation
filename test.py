import requests

url = "https://us-central1-xbot-2b603.cloudfunctions.net/jig"

data = {
    "address": "14955 SW Sophia LN",
    "count": 5
}

response = requests.post(url, json=data)

if response.ok:
    result = response.json()
    if "jigs" in result:
        print("\n\n")
        print("Jigged addresses:")
        for addr in result["jigs"]:
            print(f"- {addr}")
        print("\n\n")
    else:
        print("Response JSON:", result)
else:
    print(f"Request failed with status {response.status_code}: {response.text}")
