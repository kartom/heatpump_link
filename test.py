from datetime import datetime
from time import sleep
import configparser
import paho.mqtt.client as mqtt
import serial
import platform


def debug_wait():
    """Waiting so that communication not occurs an even minute to no collide with existing communication"""
    print(datetime.now())
    second = (datetime.now().second + 3) % 60
    if second < 5:
        print("Waiting {} seconds".format(5 - second))
        sleep(5 - second);
    print(datetime.now())


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + result(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe('heatpump/parameter/+/set')


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + result(msg.payload))


def test_mqtt():
    config = configparser.ConfigParser()
    config.read("config.ini")

    client = mqtt.Client("heatpump-link")
    client.on_connect = on_connect
    client.on_message = on_message
    host = config["MQTT"]["HOST"]
    port = int(config["MQTT"]["PORT"])
    interval = int(config["APP"]["INTERVAL"])
    keepalive = int(interval + interval / 2)
    client.connect(host=host, port=port, keepalive=keepalive)

    start = datetime.now()
    while (datetime.now() - start).total_seconds() < 60:
        client.loop(timeout=1.0)


def read_response(ser: serial.Serial) -> str:
    result = ""
    while True:
        c = ser.read().decode()
        print("Got: {}".format(c))
        if c == "#":
            break
        result += c
    return result


def read_error(ser: serial.Serial) -> int:
    ser.write(b'e')  # Command read error
    return int(read_response(ser))


def read_status(ser: serial.Serial) -> int:
    ser.write(b's')
    return int(read_response(ser))


def read_counter(ser: serial.Serial) -> int:
    ser.write(b'c')
    res = int(read_response(ser))
    if res < 0:
        res = res+65536
    return res


def read_temperature(ser: serial.Serial, idx: bytes) -> float:
    ser.write(b't')
    print(bytes([48+idx]))
    ser.write(bytes([48+idx]))
    return float(read_response(ser))


if __name__ == '__main__':
    if platform.system() == "Linux":
        ser = serial.Serial(port="/dev/ttyS0", baudrate=19200)
    else:
        ser = serial.Serial("COM1")
    debug_wait()
    print("Read temperature 0:")
    print(read_temperature(ser, 0))
    print("Read error:")
    print(read_error(ser))
    print("Read status:")
    print(read_status(ser))
    print("Read counter:")
    print(read_counter(ser))
