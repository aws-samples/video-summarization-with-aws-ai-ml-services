import json
import boto3
from botocore.exceptions import ClientError
import os


def lambda_handler(event, context):
    records = event["Records"]
    message = records[0]["body"]

    # Deserialize the message body from the string representation
    message_body = json.loads(message)

    # Access the values in the JSON payload
    taskId = records[0]["messageId"]
    userId = message_body["userId"]
    video_name = message_body["video_name"]
    voiceId = message_body["voiceId"]
    gender = message_body["gender"]

    input = {
        "userId": userId,
        "taskId": taskId,
        "video_name": video_name,
        "voiceId": voiceId,
        "gender": gender,
    }
    stepfunctions = boto3.client("stepfunctions")
    sfResponse = stepfunctions.start_execution(
        stateMachineArn=os.environ["StepFunction"], input=json.dumps(input)
    )

    return {"statusCode": 200}
