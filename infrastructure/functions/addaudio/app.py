import boto3
from botocore.exceptions import ClientError
import os

mediconvert_client = boto3.client("mediaconvert")
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
    endpoint_url = mediconvert_client.describe_endpoints(Mode="GET_ONLY")
    endpoint_url = endpoint_url["Endpoints"][0]["Url"]
    userId = event["VSHParams"]["userId"]
    taskId = event["VSHParams"]["taskId"]

    video_file = (
        "s3://"
        + bucket_output_videos
        + "/"
        + userId
        + "/"
        + taskId
        + "/"
        + os.path.splitext(os.path.basename(video_name))[0]
        + "_raw.mp4"
    )
    audio_file = event["VSHParams"]["PollyAudioParams"]["outputUri"]
    subtitle_file = "s3://" + bucket_transcripts + "/" + taskId + "-summary.srt"
    output_file = (
        "s3://"
        + bucket_output_videos
        + "/"
        + userId
        + "/"
        + taskId
        + "/"
        + os.path.splitext(os.path.basename(video_name))[0]
    )

    narrator_vol = 0
    music_vol_level = 50
    music_vol = -60 + 60 * music_vol_level / 100

    mediaconvertTaskId = create_mediaconvert_task(
        endpoint_url,
        taskId,
        media_convert_queue,
        iam_role,
        video_file,
        audio_file,
        output_file,
        narrator_vol,
        music_vol,
        subtitle_file,
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
    output_file,
    narrator_vol,
    music_vol,
    subtitle_file,
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
                            "AudioDescriptions": [
                                {
                                    "AudioSourceName": "Audio Selector Group 1",
                                    "CodecSettings": {
                                        "Codec": "AAC",
                                        "AacSettings": {
                                            "Bitrate": 96000,
                                            "CodingMode": "CODING_MODE_2_0",
                                            "SampleRate": 48000,
                                        },
                                    },
                                }
                            ],
                            "CaptionDescriptions": [
                                {
                                    "CaptionSelectorName": "Captions Selector 1",
                                    "DestinationSettings": {
                                        "DestinationType": "BURN_IN",
                                        "BurninDestinationSettings": {
                                            "BackgroundOpacity": 100,
                                            "FontSize": 18,
                                            "FontColor": "WHITE",
                                            "ApplyFontColor": "ALL_TEXT",
                                            "BackgroundColor": "BLACK",
                                        },
                                    },
                                }
                            ],
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
                    "AudioSelectors": {
                        "Audio Selector 1": {
                            "DefaultSelection": "NOT_DEFAULT",
                            "ExternalAudioFileInput": audio_file,
                        },
                    },
                    "AudioSelectorGroups": {
                        "Audio Selector Group 1": {
                            "AudioSelectorNames": ["Audio Selector 1"]
                        }
                    },
                    "VideoSelector": {},
                    "TimecodeSource": "ZEROBASED",
                    "CaptionSelectors": {
                        "Captions Selector 1": {
                            "SourceSettings": {
                                "SourceType": "SRT",
                                "FileSourceSettings": {"SourceFile": subtitle_file},
                            }
                        }
                    },
                    "FileInput": video_file,
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
