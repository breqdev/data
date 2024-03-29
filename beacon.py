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


# Now drawing from 'AC Power'
#  -InternalBattery-0 (id=22478947)       9%; AC attached; not charging present: true

# Now drawing from 'Battery Power'
#  -InternalBattery-0 (id=22478947)       9%; discharging; 0:38 remaining present: true
#         Battery Warning: Early


def ping():
    output = subprocess.check_output(["pmset", "-g", "batt"]).decode("utf-8")
    lines = output.split("\n")
    try:
        source = lines[0].removeprefix("Now drawing from '").split("'")[0]
        percentage = int(re.search(r"\d+%", lines[1]).group()[:-1])
        time = re.search(r"\d+:\d+", lines[1]).group()
    except:
        source = "Unknown"
        percentage = 0
        time = "0:00"

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
                "percentage": percentage,
                "time_remaining": time,
            },
            "volume": int(volume),
            "focused_app": focused_app,
        },
    ).raise_for_status()


schedule.every(15).seconds.do(ping)


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


schedule_thread = threading.Thread(target=run_schedule)
schedule_thread.start()


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)

    return image


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
