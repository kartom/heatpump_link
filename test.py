from datetime import datetime
from time import sleep
import configparser
import paho.mqtt.client as mqtt
import serial
import platform

parameters = {"filter": 0,  # Filter time in seconds for temperature measurements
              "sp_temp": 1,  # Set point for the house temperature
              "acc_min_temp": 2,  # Minimum temperature i the middle of the acc tank before the heat pump is started
              "stop_offset": 3,  # Offset for all temperature comparisons that can stop the heat pump
              "water_min_temp": 4,  # Temperature of the tap water that starts tap water production
              "max_return_temp": 5,  # Temperature to the heat pump that aborts initial tap water production
              "water_hot_temp": 6,  # Temperature of tap water that does not require final heating of tap water
              "supply_tc_k": 7,  # Supply temperature controller gain
              "house_tc_k": 8,  # House temperature controller gain
              "supply_tc_ti": 9,  # Supply temperature controller integration time [s]
              "house_tc_ti": 10,  # House temperature controller integration time [s]
              "supply_tc_td": 11,  # Supply temperature controller derivative time [s]
              "house_tc_td": 12,  # House temperature controller derivative time [s]
              "supply_tc_min": 13,  # Supply temperature controller, output low limit
              "house_tc_min": 14,  # House temperature controller, output low limit
              "supply_tc_max": 15,  # Supply temperature controller, output high limit
              "house_tc_max": 16,  # House temperature controller, output high limit
              "changeover_time": 17  # Change over time when switching to tap water production
              }


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
    print("Connected with result code {}".format(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe('heatpump/parameter/+/set')


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + msg.payload)


def connect_mqtt(host: str, port: int) -> mqtt.Client:
    client = mqtt.Client("heatpump-link")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=host, port=port)
    return client


def read_response(ser: serial.Serial) -> str:
    result = ""
    while True:
        c = ser.read().decode()
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
        res = res + 65536
    return res


def read_temperature(ser: serial.Serial, idx: bytes) -> float:
    ser.write(b't')
    ser.write(bytes([48 + idx]))
    return float(read_response(ser))


def read_parameter(ser: serial.Serial, idx: bytes) -> float:
    ser.write(b'p')
    ser.write(bytes([48 + idx]))
    return float(read_response(ser))


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")

    mqtt_client = connect_mqtt(host=config["MQTT"]["HOST"], port=int(config["MQTT"]["PORT"]))

    mqtt_client.loop_start()
    debug_wait()

    if platform.system() == "Linux":
        ser = serial.Serial(port="/dev/ttyS0", baudrate=19200)
        for par, idx in parameters.items():
            mqtt_client.publish("heatpump/parameter/{}".format(par), read_parameter(ser, idx), qos=1, retain=True)
    else:
        for par, idx in parameters.items():
            mqtt_client.publish("heatpump/parameter/{}".format(par), idx, qos=1, retain=True)

    sleep(20)
    mqtt_client.loop_stop()
