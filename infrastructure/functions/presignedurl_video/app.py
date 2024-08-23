import json
import logging
import boto3
from botocore.exceptions import ClientError
import os
import time

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    bucket_name = os.environ["bucket_videos"]
    userId = event["queryStringParameters"]["userId"]
    object_name = event["queryStringParameters"]["object_name"]
    content_type = get_content_type(object_name)

    if content_type != "video/mp4":
        raise Exception("Unsupported image format")

    name, extension = os.path.splitext(object_name)

    if event["queryStringParameters"]["type"] == "post":
        response = create_presigned_post(bucket_name, f"{userId}/{object_name}")
    else:  # get
        response = create_presigned_url(bucket_name, f"{userId}/{object_name}")
    if response is None:
        exit(1)

    return {"statusCode": 200, "body": json.dumps(response)}


def create_presigned_post(
    bucket_name, object_name, fields=None, conditions=None, expiration=3600
):
    """Generate a presigned URL S3 POST request to upload a file

    :param bucket_name: string
    :param object_name: string
    :param fields: Dictionary of prefilled form fields
    :param conditions: List of conditions to include in the policy
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Dictionary with the following keys:
        url: URL to post to
        fields: Dictionary of form fields and values to submit with the POST
    :return: None if error.
    """

    # Generate a presigned S3 POST URL
    try:
        response = s3_client.generate_presigned_post(
            bucket_name,
            object_name,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL and required fields
    return response


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


def get_content_type(filename):
    mime_types = {"mp4": "video/mp4"}

    # Get the file extension from the filename
    file_extension = filename.split(".")[-1].lower()

    return mime_types.get(file_extension, "application/octet-stream")
