import boto3
from botocore.exceptions import ClientError
import os

s3_client = boto3.client("s3")
dynamodb_client = boto3.resource("dynamodb")


def lambda_handler(event, context):
    bucket_videos = os.environ["bucket_videos"]
    bucket_transcripts = os.environ["bucket_transcripts"]
    bucket_audio = os.environ["bucket_audio"]
    bucket_output_videos = os.environ["bucket_output_videos"]
    video_name = event["VSHParams"]["video_name"]
    media_convert_queue = os.environ["media_convert_queue"]
    iam_role = os.environ["iam_role"]
    endpoint_url = boto3.client("mediaconvert").describe_endpoints(Mode="GET_ONLY")
    endpoint_url = endpoint_url["Endpoints"][0]["Url"]
    userId = event["VSHParams"]["userId"]
    taskId = event["VSHParams"]["taskId"]

    video_file = "s3://" + bucket_videos + "/" + video_name
    audio_file = event["VSHParams"]["PollyAudioParams"]["outputUri"]
    output_file = "s3://" + bucket_output_videos + "/" + userId + "/" + taskId + "/"

    timecodes = (
        s3_client.get_object(Bucket=bucket_transcripts, Key=taskId + ".dat")["Body"]
        .read()
        .decode("utf-8-sig")
    )
    to_json = lambda s: [
        {"StartTimecode": t1, "EndTimecode": t2}
        for t1, t2 in (line.split(",") for line in s.split("\n") if line.strip())
    ]
    timecodes = to_json(timecodes)

    mediaconvertTaskId = create_mediaconvert_task(
        endpoint_url,
        taskId,
        media_convert_queue,
        iam_role,
        video_file,
        audio_file,
        timecodes,
        output_file,
    )

    updateTaskStatus(
        os.environ["vsh_dynamodb_table"],
        userId,
        taskId,
        mediaconvertTaskId,
        video_name,
        event["TaskToken"],
    )

    return {"statusCode": 200}


def create_mediaconvert_task(
    endpoint_url,
    taskId,
    media_convert_queue,
    iam_role,
    video_file,
    audio_file,
    timecodes,
    output_file,
):
    media_convert = boto3.client("mediaconvert", endpoint_url=endpoint_url)
    response = media_convert.create_job(
        Queue=media_convert_queue,
        UserMetadata={},
        Role=iam_role,
        Settings={
            "TimecodeConfig": {"Source": "ZEROBASED"},
            "OutputGroups": [
                {
                    "Name": "File Group",
                    "Outputs": [
                        {
                            "ContainerSettings": {
                                "Container": "MP4",
                                "Mp4Settings": {},
                            },
                            "VideoDescription": {
                                "CodecSettings": {
                                    "Codec": "H_264",
                                    "H264Settings": {
                                        "MaxBitrate": 40000000,
                                        "RateControlMode": "QVBR",
                                        "SceneChangeDetect": "TRANSITION_DETECTION",
                                    },
                                }
                            },
                            "NameModifier": "_raw",
                        }
                    ],
                    "OutputGroupSettings": {
                        "Type": "FILE_GROUP_SETTINGS",
                        "FileGroupSettings": {"Destination": output_file},
                    },
                }
            ],
            "Inputs": [
                {
                    "VideoSelector": {},
                    "TimecodeSource": "ZEROBASED",
                    "FileInput": video_file,
                    "InputClippings": timecodes,
                }
            ],
        },
        AccelerationSettings={"Mode": "DISABLED"},
        StatusUpdateInterval="SECONDS_60",
        Priority=0,
    )
    return response["Job"]["Id"]


def updateTaskStatus(
    dynamodb_table, userId, taskId, mediaconvertTaskId, video_name, sfToken
):
    output_filename = (
        userId
        + "/"
        + taskId
        + "/"
        + os.path.splitext(os.path.basename(video_name))[0]
        + ".mp4"
    )

    table = dynamodb_client.Table(dynamodb_table)
    dynamodbResponse = table.update_item(
        Key={"TaskId": taskId},
        UpdateExpression="SET #att1 = :value1, #att2 = :value2, #att3 = :value3",
        ExpressionAttributeValues={
            ":value1": mediaconvertTaskId,
            ":value2": output_filename,
            ":value3": sfToken,
        },
        ExpressionAttributeNames={
            "#att1": "MediaConvertTaskId",
            "#att2": "Output",
            "#att3": "LambdaMediaConvertTaskToken",
        },
    )
