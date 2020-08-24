# AWS IoT and LoRa: Collecting and Analyzing IoT Data in Near Real-Time with AWS IoT, LoRa, and LoRaWAN

Code for the post, [AWS IoT and LoRa: Collecting and Analyzing IoT Data in Near Real-Time with AWS IoT, LoRa, and LoRaWAN](https://programmaticponderings.com/).

## Deploy CloudFormation Stack

```bash
aws cloudformation create-stack \
  --stack-name lora-iot-demo \
  --template-body file://cloudformation/iot-analytics.yaml \
  --parameters ParameterKey=ProjectName,ParameterValue=lora-iot-demo \
               ParameterKey=IoTTopicName,ParameterValue=lora-iot-demo \
  --capabilities CAPABILITY_NAMED_IAM
```
