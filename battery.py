import time
from functools import reduce

import pystray
import schedule
import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from pystray import MenuItem, Menu
from usb.backend import libusb1
from usb.core import Device

# Find the product ID of your mouse from this list
# https://github.com/openrazer/openrazer/blob/master/driver/razermouse_driver.h
# The tuple is (product_id, is_wireless)
PRODUCT_WIRELESS_LIST = [
    (0x00B6, False),
    (0x00B7, True),
    (0x00C2, False),
    (0x00C3, True),
]

# Razor Vendor ID. No need to change this
VENDOR_ID = 0x1532

# Find the transaction id from this switch statement
# https://github.com/openrazer/openrazer/blob/master/driver/razermouse_driver.c#L1176
TRANSACTION_ID = 0x1F

# Refresh interval in seconds. Default is 5 minutes
REFRESH_INTERVAL = 300

# IDK why you would want to change this. It's the size of the image. Keep it 64.
IMG_SIZE = 256

# Don't touch this. Just a funny global variable to track state.
continue_running = True


def get_mouse() -> tuple[Device, bool]:
    backend = libusb1.get_backend()

    for product_id, is_wireless in PRODUCT_WIRELESS_LIST:
        mouse = usb.core.find(idVendor=VENDOR_ID, idProduct=product_id, backend=backend)

        if mouse:
            return mouse, is_wireless

    raise RuntimeError(
        f"The specified mouse (PID:{', '.join(map(lambda a: a[0], PRODUCT_WIRELESS_LIST))}) cannot be found."
    )


def data_buffer() -> bytes:
    # adapted from https://github.com/rsmith-nl/scripts/blob/main/set-ornata-chroma-rgb.py
    # the first 8 bytes in order from left to right
    # status + transaction_id.id + remaining packets (\x00\x00) + protocol_type + command_class + command_id + data_size
    buf = [0] * 90
    buf[1] = TRANSACTION_ID
    buf[5] = 0x02
    buf[6] = 0x07
    buf[7] = 0x80
    buf[88] = reduce(lambda x, y: x ^ y, buf[2:8])
    return bytes(buf)


def get_battery() -> int:
    [mouse, wireless] = get_mouse()
    msg = data_buffer()

    mouse.set_configuration()
    usb.util.claim_interface(mouse, 0)

    mouse.ctrl_transfer(
        bmRequestType=0x21,
        bRequest=0x09,
        wValue=0x300,
        data_or_wLength=msg,
        wIndex=0x00,
    )
    usb.util.dispose_resources(mouse)

    if wireless:
        time.sleep(0.5)

    result = mouse.ctrl_transfer(
        bmRequestType=0xA1, bRequest=0x01, wValue=0x300, data_or_wLength=90, wIndex=0x00
    )
    usb.util.dispose_resources(mouse)
    usb.util.release_interface(mouse, 0)

    return int(result[9] / 255 * 100)


def text_width(text: str, font: FreeTypeFont):
    draw = ImageDraw.Draw(Image.new("1", (1, 1)))
    _, _, w, h = draw.textbbox(xy=(0, 0), text=text, font=font)
    return w, h


def color_font_size_per_battery(battery: int) -> tuple[str, int]:
    if battery == 100:
        return "#0abde3", 147
    if battery > 95:
        return "#0abde3", 219
    if battery < 10:
        return "#ff6b6b", 258
    return "#7bed9f", 219


def battery_img(battery: int):
    str_bat = str(battery)

    image = Image.new("RGBA", (IMG_SIZE, IMG_SIZE))
    ctx = ImageDraw.Draw(image)

    color, font_size = color_font_size_per_battery(battery)
    font = ImageFont.truetype("Roboto-Regular.ttf", font_size)

    w, h = text_width(str_bat, font)

    ctx.text(
        ((IMG_SIZE - w) // 2, IMG_SIZE // 2 - 2 * h // 3),
        str_bat,
        color,
        font,
    )

    return image


def refresh_tray_icon(icon: pystray.Icon):
    bat = get_battery()
    icon.title = f"Battery: {bat}%"
    icon.icon = battery_img(bat)


def end_script(icon: pystray.Icon):
    global continue_running
    continue_running = False
    icon.stop()


def schedule_job(icon: pystray.Icon):
    icon.visible = True
    schedule.every(REFRESH_INTERVAL).seconds.do(refresh_tray_icon, icon)
    while continue_running:
        schedule.run_pending()
        time.sleep(1)


def main():
    icon = pystray.Icon(
        name="DeathAdder V3 Battery",
        menu=Menu(MenuItem("Refresh", refresh_tray_icon), MenuItem("Exit", end_script)),
    )
    refresh_tray_icon(icon)
    icon.run(setup=schedule_job)


if __name__ == "__main__":
    main()
