import logging
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import os
import datetime

s3_client = boto3.client("s3")
dynamodb_client = boto3.resource("dynamodb")
stepfunctions_client = boto3.client("stepfunctions")


def lambda_handler(event, context):
    dynamodb_table = os.environ["vsh_dynamodb_table"]

    table = dynamodb_client.Table(dynamodb_table)
    mediaconvertTaskId = event["detail"]["jobId"]
    queue = event["detail"]["queue"]
    response = table.query(
        IndexName="MediaConvertGSI",
        KeyConditionExpression=Key("MediaConvertTaskId").eq(mediaconvertTaskId),
    )
    item = response["Items"][0]
    sfTaskToken = item["LambdaMediaConvertTaskToken"]

    # sendTaskSuccess to Step Function to notify mediaconvert has successfully finished the job
    sfResponse = stepfunctions_client.send_task_success(
        taskToken=sfTaskToken, output="{}"
    )

    if queue == os.environ["media_convert_queue_release"]:
        video_name = parse_s3_path(
            event["detail"]["outputGroupDetails"][0]["outputDetails"][0][
                "outputFilePaths"
            ][0]
        )
        updateTaskStatus(
            dynamodb_table,
            item["TaskId"],
            "Complete",
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    return {"statusCode": 200}


def updateTaskStatus(dynamodb_table, taskId, status, endTime):
    table = dynamodb_client.Table(dynamodb_table)
    dynamodbResponse = table.update_item(
        Key={"TaskId": taskId},
        UpdateExpression="SET #st = :value1, #et = :value2",
        ExpressionAttributeValues={":value1": status, ":value2": endTime},
        ExpressionAttributeNames={"#st": "Status", "#et": "EndTime"},
    )


def create_presigned_url(
    bucket_name, object_name, expiration=os.environ["task_expire_time"]
):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


def parse_s3_path(s3_path):
    # Remove the 's3://' prefix if present
    if s3_path.startswith("s3://"):
        s3_path = s3_path[5:]

    # Split the path into bucket and object key
    parts = s3_path.split("/", 1)
    bucket_name = parts[0]
    object_key = parts[1] if len(parts) > 1 else ""

    return object_key
