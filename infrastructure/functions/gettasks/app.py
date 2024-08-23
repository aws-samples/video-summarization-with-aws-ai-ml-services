import json
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import os
import logging

dynamodb_client = boto3.resource("dynamodb")
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    bucket_input_video = os.environ["bucket_input_video"]
    bucket_output_video = os.environ["bucket_output_video"]
    dynamodb_table = os.environ["vsh_dynamodb_table"]
    userId = event["queryStringParameters"]["userId"]

    table = dynamodb_client.Table(dynamodb_table)
    response = table.query(
        IndexName="UserIdGSI", KeyConditionExpression=Key("UserId").eq(userId)
    )
    items = response["Items"]
    response = []
    for item in items:
        inputUrl = create_presigned_url(bucket_input_video, item["Input"])
        if item["Status"] == "Complete":
            outputUrl = create_presigned_url(bucket_output_video, item["Output"])
        else:
            outputUrl = ""
        response.append(
            {
                "taskId": item["TaskId"],
                "inputFilename": item["Input"],
                "inputUrl": inputUrl,
                "pollyVoice": item["PollyVoice"],
                "status": item["Status"],
                "started": item["Started"],
                "endTime": item["EndTime"],
                "outputFilename": item["Output"],
                "outputUrl": outputUrl,
                "taskType": item["TaskType"],
            }
        )

    return {"statusCode": 200, "body": json.dumps(response)}


def create_presigned_url(bucket_name, object_name, expiration=3600):
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
