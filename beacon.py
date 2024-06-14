import os
import time
import requests
import schedule
import threading
import pystray
import subprocess
import re
from dotenv import load_dotenv
from PIL import Image, ImageDraw

load_dotenv()

enabled = True

def ping():
    if not enabled:
        return

    try:
        output = subprocess.check_output(["pmset", "-g", "batt"]).decode("utf-8")
        lines = output.split("\n")
        source = lines[0].removeprefix("Now drawing from '").split("'")[0]
        percentage = re.search(r"\d+\%", lines[1]).group()[:-1]
        try:
            time = re.search(r"\d+:\d+", lines[1]).group()
        except Exception as e:
            time = "N/A"

        volume = subprocess.check_output(
            ["osascript", "-e", "output volume of (get volume settings)"]
        ).decode("utf-8")

        focused_app = (
            subprocess.check_output(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of first application process whose frontmost is true',
                ]
            )
            .decode("utf-8")
            .strip()
        )

        requests.post(
            os.environ.get("BEACON_URL"),
            json={
                "token": os.environ.get("BEACON_TOKEN"),
                "battery": {
                    "source": source,
                    "percentage": percentage + "%",
                    "time_remaining": time,
                },
                "volume": volume.strip() + "%",
                "focused_app": focused_app,
            },
        ).raise_for_status()
    except Exception as e:
        print(e)


schedule.every(15).seconds.do(ping)


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


schedule_thread = threading.Thread(target=run_schedule)
schedule_thread.start()


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    return Image.open("beacon.png")


def toggle_enable(icon: pystray.Icon, item: pystray.MenuItem):
    global enabled
    enabled = not enabled
    icon.update_menu()


menu = pystray.Menu(
    pystray.MenuItem("data.breq.dev", lambda icon, item: None, enabled=False),
    pystray.MenuItem(
        lambda icon: "✅ Status: Enabled" if enabled else "🚫 Status: Disabled",
        lambda icon, item: None,
        enabled=False,
    ),
    pystray.MenuItem(
        lambda icon: "Disable" if enabled else "Enable",
        toggle_enable,
    ),
)

# In order for the icon to be displayed, you must provide an icon
icon = pystray.Icon("test name", icon=create_image(64, 64, "black", "white"), menu=menu)


# To finally show you icon, call run
icon.run()

schedule_thread.join()
