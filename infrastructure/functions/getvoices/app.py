import json
import boto3
from botocore.exceptions import ClientError

polly_client = boto3.client("polly")


def lambda_handler(event, context):
    language = event["queryStringParameters"]["language"]
    gender = event["queryStringParameters"]["gender"]

    response = polly_client.describe_voices(Engine="neural", LanguageCode=language)

    voices = []
    for voice in response["Voices"]:
        if voice["Gender"].lower() == gender.lower():
            voices.append(voice)

    response["Voices"] = voices

    return {"statusCode": 200, "body": json.dumps(response)}
