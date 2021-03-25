# AWS CLI Commands

Run the following AWS CLI commands after CloudFormation stack completes successfully.

```bash
# set variables
thingName=lora-iot-gateway-01
thingPolicy=LoRaDevicePolicy
thingType=LoRaIoTGateway
thingGroup=LoRaIoTGateways
thingBillingGroup=IoTGateways

# create directory to store certs
mkdir ${thingName}

# create certs
aws iot create-keys-and-certificate \
    --certificate-pem-outfile "${thingName}/${thingName}.cert.pem" \
    --public-key-outfile "${thingName}/${thingName}.public.key" \
    --private-key-outfile "${thingName}/${thingName}.private.key" \
    --set-as-active

# assuming you only have one certificate registered
certificate=$(aws iot list-certificates | jq '.[][] | .certificateArn')

# alternately, for a specific certificate if you have more than one
aws iot list-certificates

# then change the value below
certificate=arn:aws:iot:us-east-1:123456789012:cert/<certificate>

# create and associate thing, group, policy, billing group
aws iot attach-policy \
    --policy-name $thingPolicy \
    --target $certificate

aws iot attach-thing-principal \
    --thing-name $thingName \
    --principal $certificate

aws iot create-thing-type \
    --thing-type-name $thingType \
    --thing-type-properties "thingTypeDescription=LoRaWAN IoT Gateway"

aws iot create-thing-group \
    --thing-group-name $thingGroup \
    --thing-group-properties "thingGroupDescription=\"LoRaWAN IoT Gateway Thing Group\", attributePayload={attributes={Manufacturer=RaspberryPiFoundation}}"

aws iot add-thing-to-thing-group \
    --thing-name $thingName \
    --thing-group-name $thingGroup

aws iot create-billing-group \
    --billing-group-name $thingBillingGroup \
    --billing-group-properties "billingGroupDescription=\"Gateway Billing Group\""

aws iot add-thing-to-billing-group \
    --thing-name $thingName \
    --billing-group-name $thingBillingGroup

aws iot update-thing \
    --thing-name $thingName \
    --thing-type-name $thingType \
    --attribute-payload "{\"attributes\": {\"GatewayMfr\":\"RaspberryPiFoundation\", \"LoRaMfr\":\"REYAX\", \"LoRaModel\":\"RYLR896\"}}"

aws iot describe-thing \
    --thing-name $thingName
```

## Copy certificate to LoRaWAN Gateway

```shell
scp -i ~/.ssh/rasppi lora-iot-gateway-01/*.* \
    pi@192.168.1.8:~/lora-iot-gateway-01-creds/
```

## Run commands from on LoRaWAN Gateway

Installing the latest AWS IoT Device SDK v2 for Python

```shell
# https://github.com/aws/aws-iot-device-sdk-python-v2
python3 -m pip install awsiotsdk
```
```shell

# start main program (update endpoint)
python3 -m pip install --user -r requirements.txt
sh ./rasppi_lora_receiver_aws.sh your-endpoint-id.iot.us-east-1.amazonaws.com

# confirm transceiver are functioning correctly
tail -f output.log

sudo tcpdump -i wlan0 port 443 -vvv
```

```shell
aws cloudformation delete-stack --stack-name lora-iot-demo
```