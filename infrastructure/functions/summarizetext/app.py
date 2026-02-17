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

    user_message = f"""Create a narrative summary of the following video transcript. Write it as a flowing storyline that could be read aloud as voice narration.

{original_text}

Requirements:
- Keep the summary between 150-225 words (approximately 60-90 seconds when spoken)
- Write in plain prose without any headlines, titles, sections, bullet points, or formatting
- Keep the natural flow and story arc of the original content
- Each sentence should closely mirror the meaning of sentences in the original transcript
- Only include information present in the transcript
- Write in a conversational tone suitable for voice-over narration"""

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.25,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "system": "You are a narrator creating voice-over scripts. Output only the narration text with no formatting, headers, or meta-commentary."
        }
    )
    response = bedrock_client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    summarized_text = response_body["content"][0]["text"]

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
