import os
import time
import requests
import schedule
from dotenv import load_dotenv

load_dotenv()


def ping():
    requests.post(
        os.environ.get("BEACON_URL"),
        json={
            "token": os.environ.get("BEACON_TOKEN"),
        },
    ).raise_for_status()


schedule.every(15).seconds.do(ping)

while True:
    schedule.run_pending()
    time.sleep(1)
