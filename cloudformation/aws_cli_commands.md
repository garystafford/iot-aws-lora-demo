# AWS CLI Commands

Run after CloudFormation stack is deployed.

```bash
# variables
thingName=lora-iot-gateway-01
thingPolicy=LoRaDevicePolicy
thingType=LoRaIoTGateway
thingGroup=LoRaIoTGateways
thingBillingGroup=LoRaIoTGateways

aws iot create-keys-and-certificate \
    --certificate-pem-outfile "${thingName}/${thingName}.cert.pem" \
    --public-key-outfile "${thingName}/${thingName}.public.key" \
    --private-key-outfile "${thingName}/${thingName}.private.key"
    --set-as-active


# for a specific certificate
aws iot list-certificates
# find your certificate
certificate=arn:aws:iot:us-east-1:<account>:cert/<certificate>

# assuming only one certificate
certificate=$(aws iot list-certificates | jq '.[][] | .certificateArn')

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
