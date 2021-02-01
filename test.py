from datetime import datetime, timedelta
from time import sleep
import configparser
import paho.mqtt.client as mqtt
import serial
import platform
import json

parameters = {
    "filter": (b'p', 0),  # Filter time in seconds for temperature measurements
    "sp_temp": (b'p', 1),  # Setpoint for the house temperature
    "acc_min_temp": (b'p', 2),  # Minimum temperature i the middle of the acc tank before the heat pump is started
    "stop_offset": (b'p', 3),  # Offset for all temperature comparisons that can stop the heat pump
    "water_min_temp": (b'p', 4),  # Temperature of the tap water that starts tap water production
    "max_return_temp": (b'p', 5),  # Temperature to the heat pump that aborts initial tap water production
    "water_hot_temp": (b'p', 6),  # Temperature of tap water that does not require final heating of tap water
    "supply_tc_k": (b'p', 7),  # Supply temperature controller gain
    "supply_tc_ti": (b'p', 9),  # Supply temperature controller integration time [s]
    "supply_tc_td": (b'p', 11),  # Supply temperature controller derivative time [s]
    "supply_tc_out_min": (b'p', 13),  # Supply temperature controller, output low limit
    "supply_tc_out_max": (b'p', 15),  # Supply temperature controller, output high limit
    "house_tc_k": (b'p', 8),  # House temperature controller gain
    "house_tc_ti": (b'p', 10),  # House temperature controller integration time [s]
    "house_tc_td": (b'p', 12),  # House temperature controller derivative time [s]
    "house_tc_out_min": (b'p', 14),  # House temperature controller, output low limit
    "house_tc_out_max": (b'p', 16),  # House temperature controller, output high limit
    "changeover_time": (b'p', 17)  # Change over time when switching to tap water production
}

values = {
    "house/actual_temp": (b't', 0),
    "house/sp_temp": (b'p', 1),
    "house/outdoor_temp": (b't', 6),
    "supply/temp": (b't', 1),
    "supply/min_temp": (b'p', 14),
    "supply/max_temp": (b'p', 16),
    "supply/valve": (b'o', 0),
    "supply/sp_temp": (b'o', 1),
    "tap_water/temp": (b't', 2),
    "accumulator/middle_temp": (b't', 3),
    "accumulator/bottom_temp": (b't', 4),
    "accumulator/top_temp": (b't', 5),
    "heatpump/status": (b's', None),
    "heatpump/brine_in_temp": (b't', 7),
    "heatpump/brine_out_temp": (b't', 8),
    "heatpump/return_temp": (b't', 9),
    "heatpump/supply_temp": (b't', 10),
    "heatpump/counter": (b'c', None),
    "heatpump/error": (b'e', None),
}

outputs = {
    
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


def read_value(ser: serial.Serial, value: (bytes, int)):
    cmd, index = value
    ser.write(cmd)  # Command read error
    if index is not None:
        ser.write(bytes([48 + index]))
    result = ""
    while True:
        c = ser.read().decode()
        if c == "#":
            break
        result += c
    if cmd in (b'c', b'e', b's'):
        result = int(result)
        if result < 0:
            # Fix negative counter value
            result = int(result)+65536
    else:
        result = float(result)
    return result


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")
    debug = platform.system() != "Linux"

    mqtt_client = connect_mqtt(host=config["MQTT"]["HOST"], port=int(config["MQTT"]["PORT"]))

    mqtt_client.loop_start()

    if not debug:
        ser = serial.Serial(port="/dev/ttyS0", baudrate=19200)
        debug_wait()

    res = {}
    for par, value in parameters.items():
        res[par] = read_value(ser, value) if not debug else value[1]
    mqtt_client.publish(topic="{}$implementation/config".format(config["MQTT"]["PREFIX"]),
                        payload=json.dumps({"settings": res}),
                        qos=1,
                        retain=True)

    next_time = datetime.now()
    while (next_time.second+5) % 10:
        next_time = datetime.now()

    n = 20
    while True:
        print(next_time)
        while datetime.now() < next_time:
            sleep(0.1)
        next_time = next_time+timedelta(seconds=10)
        for topic, value in values.items():
            mqtt_client.publish(topic="{}{}".format(config["MQTT"]["PREFIX"], topic),
                                payload=read_value(ser, value) if not debug else value[1],
                                qos=1,
                                retain=True)
        n -= 1
        if n <= 0:
            break

    mqtt_client.loop_stop()
