import boto3
from botocore.exceptions import ClientError
import os
import datetime

dynamodb_client = boto3.resource("dynamodb")


def lambda_handler(event, context):
    dynamodb_table = os.environ["vsh_dynamodb_table"]
    taskId = event["taskId"]
    status = "Failed"
    endTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updateTaskStatus(dynamodb_table, taskId, status, endTime)
    return {"statusCode": 200}


def updateTaskStatus(dynamodb_table, taskId, status, endTime):
    table = dynamodb_client.Table(dynamodb_table)
    dynamodbResponse = table.update_item(
        Key={"TaskId": taskId},
        UpdateExpression="SET #st = :value1, #et = :value2",
        ExpressionAttributeValues={":value1": status, ":value2": endTime},
        ExpressionAttributeNames={"#st": "Status", "#et": "EndTime"},
    )
