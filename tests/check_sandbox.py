import requests
import time


def make_request(url):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to {url}: {e}")
        exit(1)


sandbox_url = 'http://happysct-sandbox.mydomain'
health_url = f'{sandbox_url}/health'

# Lets wait for sandbox to start
for i in range(60):
    try:
        r = requests.get(health_url, timeout=5)
        if r.ok:
            break
    except Exception:
        print('Waiting for sandbox')
    time.sleep(1)

# Check some output
health_data = make_request(health_url)
if 'message' in health_data and health_data['message'] == ['I am fine']:
    pass
else:
    print(f"Error in response from {health_url}: {health_data}")
    exit(1)
