import os
import time
import requests
import schedule
import threading
import pystray
from dotenv import load_dotenv
from PIL import Image, ImageDraw

load_dotenv()

enabled = True


def ping():
    requests.post(
        os.environ.get("BEACON_URL"),
        json={
            "token": os.environ.get("BEACON_TOKEN"),
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
