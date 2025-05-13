import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv('OPENAQ_API_KEY')
headers = {'Accept': 'application/json', 'X-API-Key': api_key}

response = requests.get('https://api.openaq.org/v3/locations', params={'country': 'US', 'limit': 20}, headers=headers)

if response.status_code != 200:
    print(f"Error: {response.status_code} - {response.text}")
    exit(1)

for loc in response.json().get('results', []):
    params = [p['parameter'] for p in loc.get('parameters', [])]
    print(f"ID: {loc['id']} | Name: {loc['name']} | City: {loc.get('city', '')} | Parameters: {params}") 