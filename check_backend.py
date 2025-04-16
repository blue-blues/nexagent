import requests

try:
    print("Checking backend connection...")
    r = requests.get('http://localhost:8000', timeout=2)
    print(f'Backend status: {r.status_code}')
except Exception as e:
    print(f'Backend not available: {e}')
