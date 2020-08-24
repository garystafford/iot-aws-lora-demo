#!/bin/bash

# Author: Gary A. Stafford
# Start IoT data collector script and tails output
# Usage:
# sh ./rasppi_lora_receiver_aws.sh  \
#     lora-iot-gateway-01 \
#     a1d0wxnxn1hs7m-ats.iot.us-east-1.amazonaws.com

if [[ $# -ne 2 ]]; then
  echo "Script requires 3 parameters..."
  exit 1
fi

DEVICE=$1    # e.g. lora-iot-gateway-01
ENDPOINT=$2  # e.g. a1d0wxnxn1hs7m-ats.iot.us-east-1.amazonaws.com
GATEWAY_ID=$(cat /proc/cpuinfo | grep Serial | grep -oh [a-z0-9]*$) # e.g. 00000000f62051ce

echo "DEVICE: ${DEVICE}"
echo "ENDPOINT: ${ENDPOINT}"
echo "GATEWAY_ID: ${GATEWAY_ID}"

nohup python3 rasppi_lora_receiver_aws.py \
  --endpoint "${ENDPOINT}" \
  --cert "lora-iot-gateway-01-creds/42141a25d6-certificate.pem.crt" \
  --key "lora-iot-gateway-01-creds/42141a25d6-private.pem.key" \
  --root-ca "lora-iot-gateway-01-creds/AmazonRootCA1.pem" \
  --client-id "${DEVICE}" \
  --topic "lora-iot-demo" \
  --gateway-id "${GATEWAY_ID}" \
  --verbosity "Info" \
  --tty "/dev/ttyAMA0" \
  --baud-rate 115200 \
  >collector.log 2>&1 </dev/null &

sleep 2

tail -f collector.log
