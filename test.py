from datetime import datetime
from time import sleep
import configparser
import paho.mqtt.client as mqtt
import serial


def debug_wait():
    """Waiting so that communication not occurs an even minute to no collide with existing communication"""
    print(datetime.now())
    second = (datetime.now().second+2) % 60
    if second < 5:
        print("Waiting {} seconds".format(5-second))
        sleep(5-second);
    print(datetime.now())


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe('heatpump/parameter/+/set')


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


def test_mqtt():
    config = configparser.ConfigParser()
    config.read("config.ini")

    client = mqtt.Client("heatpump-link")
    client.on_connect = on_connect
    client.on_message = on_message
    host = config["MQTT"]["HOST"]
    port = int(config["MQTT"]["PORT"])
    interval = int(config["APP"]["INTERVAL"])
    keepalive = int(interval + interval/2)
    client.connect(host=host, port=port, keepalive=keepalive)

    start = datetime.now()
    while (datetime.now()-start).total_seconds() < 60:
        client.loop(timeout=1.0)


if __name__ == '__main__':
    ser = serial.Serial("/dev/ttyS0")
    ser.write(b't')  # Command read temperature
    ser.write(chr(0)) # Index
    str = ""
    c = ''
    while c != "#":
        str += c
        c = chr(ser.read())
    print(str)
