import json
import logging
import sys
import threading
import time
from argparse import ArgumentParser
from datetime import datetime

import serial
from awscrt import io, mqtt, auth, http, exceptions
from awsiot import mqtt_connection_builder
from colr import color as colr

# LoRaWAN IoT Sensor Demo
# Using REYAX RYLR896 transceiver modules
# http://reyax.com/wp-content/uploads/2020/01/Lora-AT-Command-RYLR40x_RYLR89x_EN.pdf
# Author: Gary Stafford
# Requirements: python3 -m pip install --user -r requirements.txt
# Usage:
# sh ./rasppi_lora_receiver_aws.sh  \
#     lora-iot-gateway-01 \
#     a1d0wxnxn1hs7m-ats.iot.us-east-1.amazonaws.com


# constants
ADDRESS = 116
NETWORK_ID = 6
PASSWORD = "92A0ECEC9000DA0DCF0CAAB0ABA2E0EF"

# global variables
count = 0  # from args
received_count = 0
received_all_event = threading.Event()


def main():
    # get args
    logging.basicConfig(filename='output.log',
                        filemode='w', level=logging.DEBUG)
    args = get_args()  # get args
    payload = ""
    lora_payload = {}

    # set log level
    io.init_logging(getattr(io.LogLevel, args.verbosity), 'stderr')

    # spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    # set MQTT connection
    mqtt_connection = set_mqtt_connection(args, client_bootstrap)

    logging.debug("Connecting to {} with client ID '{}'...".format(
        args.endpoint, args.client_id))

    connect_future = mqtt_connection.connect()

    # future.result() waits until a result is available
    connect_future.result()

    logging.debug("Connecting to REYAX RYLR896 transceiver module...")
    serial_conn = serial.Serial(
        port=args.tty,
        baudrate=int(args.baud_rate),
        timeout=5,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS
    )

    if serial_conn.isOpen():
        logging.debug("Connected!")
        set_lora_config(serial_conn)
        check_lora_config(serial_conn)

        while True:
            # read data from serial port
            serial_payload = serial_conn.readline()
            logging.debug(serial_payload)

            if len(serial_payload) >= 1:
                payload = serial_payload.decode(encoding="utf-8")
                payload = payload[:-2]
                try:
                    data = parse_payload(payload)
                    lora_payload = {
                        "ts": time.time(),
                        "data": {
                            "device_id": str(data[0]),
                            "gateway_id": str(args.gateway_id),
                            "temperature": float(data[1]),
                            "humidity": float(data[2]),
                            "pressure": float(data[3]),
                            "color": {
                                "red": float(data[4]),
                                "green": float(data[5]),
                                "blue": float(data[6]),
                                "ambient": float(data[7])
                            }
                        }
                    }
                    logging.debug(lora_payload)
                except IndexError:
                    logging.error("IndexError: {}".format(payload))
                except ValueError:
                    logging.error("ValueError: {}".format(payload))

                # publish mqtt message
                message_json = json.dumps(
                    lora_payload,
                    sort_keys=True,
                    indent=None,
                    separators=(',', ':'))

                try:
                    mqtt_connection.publish(
                        topic=args.topic,
                        payload=message_json,
                        qos=mqtt.QoS.AT_LEAST_ONCE)
                except mqtt.SubscribeError as err:
                    logging.error(".SubscribeError: {}".format(err))
                except exceptions.AwsCrtError as err:
                    logging.error("AwsCrtError: {}".format(err))


def set_mqtt_connection(args, client_bootstrap):
    if args.use_websocket:
        proxy_options = None
        if args.proxy_host:
            proxy_options = http.HttpProxyOptions(
                host_name=args.proxy_host, port=args.proxy_port)

        credentials_provider = auth.AwsCredentialsProvider.new_default_chain(
            client_bootstrap)
        mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=args.endpoint,
            client_bootstrap=client_bootstrap,
            region=args.signing_region,
            credentials_provider=credentials_provider,
            websocket_proxy_options=proxy_options,
            ca_filepath=args.root_ca,
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=args.client_id,
            clean_session=False,
            keep_alive_secs=6)

    else:
        mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=args.endpoint,
            cert_filepath=args.cert,
            pri_key_filepath=args.key,
            client_bootstrap=client_bootstrap,
            ca_filepath=args.root_ca,
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=args.client_id,
            clean_session=False,
            keep_alive_secs=6)

    return mqtt_connection


def get_args():
    parser = ArgumentParser(
        description="Send and receive messages through and MQTT connection.")
    parser.add_argument("--tty", required=True,
                        help="serial tty", default="/dev/ttyAMA0")
    parser.add_argument("--baud-rate", required=True,
                        help="serial baud rate", default=1152000)
    parser.add_argument('--endpoint', required=True, help="Your AWS IoT custom endpoint, not including a port. " +
                                                          "Ex: \"abcd123456wxyz-ats.iot.us-east-1.amazonaws.com\"")
    parser.add_argument('--cert', help="File path to your client certificate, in PEM format.")
    parser.add_argument('--key', help="File path to your private key, in PEM format.")
    parser.add_argument('--root-ca', help="File path to root certificate authority, in PEM format. " +
                                          "Necessary if MQTT server uses a certificate that's not already in " +
                                          "your trust store.")
    parser.add_argument('--client-id', default='samples-client-id',
                        help="Client ID for MQTT connection.")
    parser.add_argument('--topic', default="samples/test",
                        help="Topic to subscribe to, and publish messages to.")
    parser.add_argument('--message', default="Hello World!", help="Message to publish. " +
                                                                  "Specify empty string to publish nothing.")
    parser.add_argument('--count', default=0, type=int, help="Number of messages to publish/receive before exiting. " +
                                                             "Specify 0 to run forever.")
    parser.add_argument('--use-websocket', default=False, action='store_true',
                        help="To use a websocket instead of raw mqtt. If you specify this option you must "
                             "specify a region for signing, you can also enable proxy mode.")
    parser.add_argument('--signing-region', default='us-east-1',
                        help="If you specify --use-web-socket, this is the region that will be used for computing "
                             "the Sigv4 signature")
    parser.add_argument('--proxy-host', help="Hostname for proxy to connect to. Note: if you use this feature, " +
                                             "you will likely need to set --root-ca to the ca for your proxy.")
    parser.add_argument('--proxy-port', type=int, default=8080,
                        help="Port for proxy to connect to.")
    parser.add_argument('--verbosity', choices=[x.name for x in io.LogLevel], default=io.LogLevel.NoLogs.name,
                        help='Logging level')
    parser.add_argument("--gateway-id", help="IoT Gateway serial number")
    args = parser.parse_args()
    return args


def parse_payload(payload):
    # input: +RCV=116,29,0447383033363932003C0034|23.94|37.71|99.89|16|38|53|80,-61,56
    # output: [0447383033363932003C0034, 23.94, 37.71, 99.89, 16.0, 38.0, 53.0, 80.0]

    payload = payload.split(",")
    payload = payload[2].split("|")
    payload = [i for i in payload]
    return payload


def set_lora_config(serial_conn):
    # configures the REYAX RYLR896 transceiver module

    serial_conn.write(str.encode("AT+ADDRESS=" + str(ADDRESS) + "\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("Address set?", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+NETWORKID=" + str(NETWORK_ID) + "\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("Network Id set?", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+CPIN=" + PASSWORD + "\r\n"))
    time.sleep(1)
    serial_payload = (serial_conn.readline())[:-2]
    print("AES-128 password set?", serial_payload.decode(encoding="utf-8"))


def check_lora_config(serial_conn):
    serial_conn.write(str.encode("AT?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("Module responding?", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+ADDRESS?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("Address:", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+NETWORKID?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("Network id:", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+IPR?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("UART baud rate:", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+BAND?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("RF frequency", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+CRFOP?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("RF output power", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+MODE?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("Work mode", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+PARAMETER?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("RF parameters", serial_payload.decode(encoding="utf-8"))

    serial_conn.write(str.encode("AT+CPIN?\r\n"))
    serial_payload = (serial_conn.readline())[:-2]
    print("AES128 password of the network",
          serial_payload.decode(encoding="utf-8"))


# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(
        return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_count
    received_count += 1
    if received_count == count:
        received_all_event.set()


if __name__ == "__main__":
    sys.exit(main())
