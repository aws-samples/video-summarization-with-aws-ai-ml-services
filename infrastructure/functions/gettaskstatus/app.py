import json
import boto3
from botocore.exceptions import ClientError
import os

dynamodb_client = boto3.resource("dynamodb")
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    dynamodb_table = os.environ["vsh_dynamodb_table"]
    bucket_output_video = os.environ["bucket_output_video"]
    taskId = event["queryStringParameters"]["taskId"]

    table = dynamodb_client.Table(dynamodb_table)
    dynamoDBresponse = table.get_item(Key={"TaskId": taskId})
    if "Item" not in dynamoDBresponse:
        response = {"status": "Running", "endTime": "", "outputUrl": ""}
    elif dynamoDBresponse["Item"]["Status"] == "Complete":
        response = {
            "status": dynamoDBresponse["Item"]["Status"],
            "endTime": dynamoDBresponse["Item"]["EndTime"],
            "outputUrl": create_presigned_url(
                bucket_output_video, dynamoDBresponse["Item"]["Output"]
            ),
        }
    elif dynamoDBresponse["Item"]["Status"] == "Failed":
        response = {
            "status": dynamoDBresponse["Item"]["Status"],
            "endTime": dynamoDBresponse["Item"]["EndTime"],
            "outputUrl": "",
        }
    else:
        response = {"status": "Running", "endTime": "", "outputUrl": ""}

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
