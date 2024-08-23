import json
import boto3
from botocore.exceptions import ClientError
import os

bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.environ["bedrock_endpoint_region"],
)
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    bucket_transcripts = os.environ["bucket_transcripts"]
    taskId = event["taskId"]
    transcript_filename = taskId + ".json"

    original_text = get_text_from_s3(bucket_transcripts, transcript_filename)

    modelId = os.environ["bedrock_endpoint_model"]
    accept = "application/json"
    contentType = "application/json"

    prompt = f"""\n\nHuman: Summarize the key points from the following video content:

    {original_text} 

    \n\nThe summary should only contain information present in the video content. Do not include any new or unrelated information. Make each sentence highly semantically similar to a sentence in the video content.
    \n\nAssistant: Here is a summary of the video: """
    body = json.dumps(
        {
            "prompt": prompt,
            "max_tokens_to_sample": 1024,
            "temperature": 0.25,
            "top_p": 0.9,
            "stop_sequences": ["\\n\\nHuman:"],
        }
    )
    response = bedrock_client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    summarized_text = response_body["completion"]

    write_text_to_s3(summarized_text, bucket_transcripts, taskId + ".txt")

    return {"statusCode": 200}


def get_text_from_s3(bucket_transcripts, transcript_filename):
    response = s3_client.get_object(Bucket=bucket_transcripts, Key=transcript_filename)
    content = response["Body"].read().decode("utf-8")
    json_content = json.loads(content)
    text = json_content["results"]["transcripts"][0]["transcript"]
    return text


def write_text_to_s3(summarized_text, bucket_transcripts, summarized_filename):
    s3_client.put_object(
        Body=summarized_text, Bucket=bucket_transcripts, Key=summarized_filename
    )
