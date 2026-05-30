import time
import spidev
import RPi.GPIO as GPIO

DC = 25
RST = 27

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(DC, GPIO.OUT)
GPIO.setup(RST, GPIO.OUT)

# Reset display
GPIO.output(RST, GPIO.HIGH)
time.sleep(0.1)
GPIO.output(RST, GPIO.LOW)
time.sleep(0.1)
GPIO.output(RST, GPIO.HIGH)
time.sleep(0.1)

spi = spidev.SpiDev()
spi.open(0, 0)  # CE0
spi.max_speed_hz = 4000000
spi.mode = 0

def command(cmd):
    GPIO.output(DC, GPIO.LOW)
    spi.writebytes([cmd])

def data(val):
    GPIO.output(DC, GPIO.HIGH)
    spi.writebytes([val])

# Basic ST7789 init
command(0x36)  # Memory data access control
data(0x00)

command(0x3A)  # Interface pixel format
data(0x05)     # 16-bit color

command(0x21)  # Inversion ON

command(0x11)  # Sleep out
time.sleep(0.12)

command(0x29)  # Display ON
time.sleep(0.1)

# Set full screen address
command(0x2A)
data(0x00); data(0x00); data(0x00); data(0xEF)

command(0x2B)
data(0x00); data(0x00); data(0x00); data(0xEF)

command(0x2C)

# Fill screen white
GPIO.output(DC, GPIO.HIGH)

for _ in range(240 * 240):
    spi.writebytes([0xFF, 0xFF])  # White pixel

print("Done")
time.sleep(5)
