import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import os

dynamodb_client = boto3.resource("dynamodb")


def lambda_handler(event, context):
    dynamodb_table = os.environ["vsh_dynamodb_table"]
    table = dynamodb_client.Table(dynamodb_table)

    transcribeTaskId = event["detail"]["TranscriptionJobName"]

    response = table.query(
        IndexName="TranscribeGSI",
        KeyConditionExpression=Key("TranscribeTaskId").eq(transcribeTaskId),
    )
    item = response["Items"][0]
    sfTaskToken = item["LambdaTranscribeTaskToken"]

    # sendTaskSuccess to Step Function to notify Transcribe has successfully finished the job
    stepfunctions = boto3.client("stepfunctions")
    sfResponse = stepfunctions.send_task_success(taskToken=sfTaskToken, output="{}")

    return {"statusCode": 200}
