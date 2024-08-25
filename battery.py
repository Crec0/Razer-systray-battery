import time
from functools import reduce

import pystray
import schedule
import usb.core
import usb.util
from PIL import Image, ImageDraw
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

# IDK why you would want to change this. It's the size of the image. Keep it 64.
IMG_SIZE = 64

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


def text_width(text: str):
    draw = ImageDraw.Draw(Image.new("1", (1, 1)))
    draw.text((0, 0), text, fill="white")
    _, _, w, h = draw.textbbox(xy=(0, 0), text=text, font_size=54, stroke_width=1)
    return w, h


def text_color_per_battery(battery: int):
    if battery < 5:
        return "#ff6b81"
    if battery > 95:
        return "#70a1ff"
    return "#7bed9f"


def battery_img(battery: int):
    str_bat = str(battery)

    image = Image.new("RGBA", (IMG_SIZE, IMG_SIZE))
    ctx = ImageDraw.Draw(image)
    w, h = text_width(str_bat)
    color = text_color_per_battery(battery)

    ctx.text(
        ((IMG_SIZE - w) // 2, IMG_SIZE // 2 - 2 * h // 3),
        str_bat,
        fill=color,
        font_size=54,
        stroke_width=1,
    )

    return image


def refresh_tray_icon(icon: pystray.Icon):
    bat = get_battery()
    icon.title = f"Battery: {bat}%"
    icon.icon = battery_img(bat)


def on_clicked(icon: pystray.Icon):
    global continue_running
    continue_running = False
    icon.stop()


def schedule_job(icon: pystray.Icon):
    icon.visible = True
    schedule.every(1).minutes.do(refresh_tray_icon, icon)
    while continue_running:
        schedule.run_pending()
        time.sleep(1)


def main():
    bat = get_battery()
    icon = pystray.Icon(
        name="DeathAdder V3 Battery",
        title=f"Battery: {bat}%",
        icon=battery_img(bat),
        menu=Menu(MenuItem("Exit", on_clicked)),
    )
    icon.run(setup=schedule_job)


if __name__ == "__main__":
    main()
