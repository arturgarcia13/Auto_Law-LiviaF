import json

import requests
from config import API_KEY, SUBDOMAIN

CREATE_LEAD_URL = f"https://{SUBDOMAIN}.kommo.com/api/v4/leads?with=contacts"

body = {
    "name": "Example Lead 1",
    "price": 1000,
}

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

reponse = requests.get(CREATE_LEAD_URL, headers=headers)
response_json = reponse.json()

with open("response.json", "w", encoding="utf-8") as f:
    json.dump(response_json, f, ensure_ascii=False, indent=4)
