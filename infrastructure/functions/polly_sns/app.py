import json
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import os

dynamodb_client = boto3.resource("dynamodb")


def lambda_handler(event, context):
    dynamodb_table = os.environ["vsh_dynamodb_table"]

    table = dynamodb_client.Table(dynamodb_table)

    message = json.loads(event["Records"][0]["Sns"]["Message"])

    pollyTaskId = message["taskId"]
    response = table.query(
        IndexName="PollyGSI", KeyConditionExpression=Key("PollyTaskId").eq(pollyTaskId)
    )
    item = response["Items"][0]
    sfTaskToken = item["LambdaPollyTaskToken"]

    # sendTaskSuccess to Step Function to notify Polly has successfully generated the audio
    stepfunctions = boto3.client("stepfunctions")
    sfResponse = stepfunctions.send_task_success(
        taskToken=sfTaskToken, output=event["Records"][0]["Sns"]["Message"]
    )

    return {"statusCode": 200}
