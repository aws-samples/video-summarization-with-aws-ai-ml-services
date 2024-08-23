import json
import logging
import boto3
from botocore.exceptions import ClientError
import os
import datetime
import time

sqs_client = boto3.client("sqs")
dynamodb_client = boto3.resource("dynamodb")


def lambda_handler(event, context):
    bucket_video = os.environ["bucket_videos"]
    userId = event["queryStringParameters"]["userId"]
    video_name = event["queryStringParameters"]["video_name"]
    language = event["queryStringParameters"]["language"]
    voiceId = event["queryStringParameters"]["voiceId"]
    gender = event["queryStringParameters"]["gender"]

    input = {
        "userId": userId,
        "video_name": video_name,
        "voiceId": voiceId,
        "gender": gender,
    }
    sqs_queue_url = os.environ["sqs_queue_url"]
    response = sqs_client.send_message(
        QueueUrl=sqs_queue_url, MessageBody=json.dumps(input)
    )

    taskId = response["MessageId"]

    table = dynamodb_client.Table(os.environ["vsh_dynamodb_table"])
    started = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ttl = int(time.time() + int(os.environ["task_expire_time"]))
    dynamodbResponse = table.put_item(
        Item={
            "TaskId": taskId,
            "UserId": userId,
            "Input": video_name,
            "PollyVoice": voiceId,
            "PollyAudioTaskId": "-",
            "LambdaTaskToken": "-",
            "MediaConvertTaskId": "-",
            "Started": started,
            "EndTime": "-",
            "Status": "Running",
            "Output": "-",
            "TaskType": "-",
            "ExpireTime": ttl,
        }
    )

    response = {
        "taskId": taskId,
        "inputFilename": video_name,
        "inputUrl": create_presigned_url(bucket_video, video_name),
        "pollyVoice": voiceId,
        "started": started,
    }

    return {"statusCode": 200, "body": json.dumps(response)}


def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client("s3")
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
