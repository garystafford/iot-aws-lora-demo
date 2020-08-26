#!/bin/bash

# Author: Gary A. Stafford
# Start IoT data collector script and tails output
# Usage:
# sh ./rasppi_lora_receiver_aws.sh  \
#     a1b2c3d4e5678f-ats.iot.us-east-1.amazonaws.com

if [[ $# -ne 1 ]]; then
  echo "Script requires 1 parameter!"
  exit 1
fi

# input parameters
ENDPOINT=$1  # e.g. a1b2c3d4e5678f-ats.iot.us-east-1.amazonaws.com
DEVICE="lora-iot-gateway-01" # matches CloudFormation thing name
CERTIFICATE="${DEVICE}-certificate.pem.crt"  # e.g. lora-iot-gateway-01-certificate.pem.crt
KEY="${DEVICE}-private.pem.key"  # e.g. lora-iot-gateway-01-private.pem.key
GATEWAY_ID=$(< /proc/cpuinfo grep Serial | grep -oh "[a-z0-9]*$") # e.g. 00000000f62051ce

# output for debugging
echo "DEVICE: ${DEVICE}"
echo "ENDPOINT: ${ENDPOINT}"
echo "CERTIFICATE: ${CERTIFICATE}"
echo "KEY: ${KEY}"
echo "GATEWAY_ID: ${GATEWAY_ID}"

# call the python script
nohup python3 rasppi_lora_receiver_aws.py \
  --endpoint "${ENDPOINT}" \
  --cert "lora-iot-gateway-01-creds/${CERTIFICATE}" \
  --key "lora-iot-gateway-01-creds/${KEY}" \
  --root-ca "lora-iot-gateway-01-creds/AmazonRootCA1.pem" \
  --client-id "${DEVICE}" \
  --topic "lora-iot-demo" \
  --gateway-id "${GATEWAY_ID}" \
  --verbosity "Info" \
  --tty "/dev/ttyAMA0" \
  --baud-rate 115200 \
  >collector.log 2>&1 </dev/null &

sleep 2

# tail the log (Control-C to exit)
tail -f collector.log
