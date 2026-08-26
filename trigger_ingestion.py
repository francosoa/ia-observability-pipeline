import requests

API_URL = "http://127.0.0.1:8000/v1/ingest/pokemons?limit=50&inject_anomalies=true"

response = requests.post(API_URL)
print("Resposta da API:", response.json())