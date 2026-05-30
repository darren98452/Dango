import time
import spidev
import RPi.GPIO as GPIO
from PIL import Image

class ST7789Display:
    WIDTH = 240
    HEIGHT = 240

    def __init__(self, dc=25, rst=27, bus=0, device=0):
        self.dc = dc
        self.rst = rst

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.dc, GPIO.OUT)
        GPIO.setup(self.rst, GPIO.OUT)

        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 4000000
        self.spi.mode = 0

        self.reset()
        self.init_display()

    def reset(self):
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.rst, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.1)

    def command(self, cmd):
        GPIO.output(self.dc, GPIO.LOW)
        self.spi.writebytes([cmd])

    def data(self, val):
        GPIO.output(self.dc, GPIO.HIGH)
        self.spi.writebytes([val])

    def init_display(self):
        self.command(0x36)
        self.data(0x00)

        self.command(0x3A)
        self.data(0x05)

        self.command(0x21)  # Inversion ON

        self.command(0x11)
        time.sleep(0.12)

        self.command(0x29)
        time.sleep(0.1)

    def set_window(self):
        self.command(0x2A)
        self.data(0x00)
        self.data(0x00)
        self.data(0x00)
        self.data(0xEF)

        self.command(0x2B)
        self.data(0x00)
        self.data(0x00)
        self.data(0x00)
        self.data(0xEF)

        self.command(0x2C)

    def display_image(self, image):
        self.set_window()
        GPIO.output(self.dc, GPIO.HIGH)

        img = image.convert("RGB")
        pixels = img.load()

        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                r, g, b = pixels[x, y]
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                self.spi.writebytes([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])

    def fill_color(self, r, g, b):
        self.set_window()
        GPIO.output(self.dc, GPIO.HIGH)

        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        hi = (rgb565 >> 8) & 0xFF
        lo = rgb565 & 0xFF

        for _ in range(self.WIDTH * self.HEIGHT):
            self.spi.writebytes([hi, lo])
