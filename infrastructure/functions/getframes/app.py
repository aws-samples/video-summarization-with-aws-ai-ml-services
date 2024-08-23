import json
import re
import boto3
from botocore.exceptions import ClientError
import os
import time
import numpy as np

s3_client = boto3.client("s3")
bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.environ["bedrock_endpoint_region"],
)
polly_client = boto3.client("polly")
dynamodb_client = boto3.resource("dynamodb")
comprehend_client = boto3.client("comprehend")


def lambda_handler(event, context):
    bucket_audio = os.environ["bucket_audio"]
    bucket_transcripts = os.environ["bucket_transcripts"]
    taskId = event["VSHParams"]["taskId"]
    voiceId = event["VSHParams"]["voiceId"]

    subtitle = get_subtitle(bucket_transcripts, taskId + ".srt")
    polly_ssml = get_polly_ssml(
        bucket_audio, event["VSHParams"]["PollySSMLParams"]["outputUri"]
    )
    intro_time = get_intro(bucket_transcripts, taskId + ".json")

    original_sentences, startTimes, endTimes = srt_to_arrays(subtitle)
    (summarized_sentences, durations, best_matching_indices, ignored_indices) = (
        text_embedding(original_sentences, polly_ssml)
    )
    generate_polly_audio(bucket_audio, taskId, voiceId, intro_time, event["TaskToken"])
    get_frames(
        bucket_transcripts,
        original_sentences,
        endTimes,
        summarized_sentences,
        durations,
        best_matching_indices,
        ignored_indices,
        intro_time,
        taskId,
    )
    create_subtitle_summary(
        bucket_transcripts,
        original_sentences,
        summarized_sentences,
        durations,
        ignored_indices,
        intro_time,
        taskId,
    )

    return {"statusCode": 200}


def text_embedding(original_sentences, polly_ssml):
    summarized_sentences = []
    durations = []
    polly_ssml = polly_ssml.split("\n")
    for i in range(len(polly_ssml) - 1):
        curr = polly_ssml[i]
        next = polly_ssml[i + 1]
        if curr.strip() == "" or next.strip() == "":
            continue
        curr = json.loads(curr)
        next = json.loads(next)
        summarized_sentences.append(curr["value"])
        durations.append(int(next["time"]) - int(curr["time"]))

    model_id = os.environ["bedrock_embedding_model"]
    accept = "application/json"
    content_type = "application/json"
    original_embeddings = []
    for str in original_sentences:
        body = json.dumps({"inputText": str})
        response = bedrock_client.invoke_model(
            body=body, modelId=model_id, accept=accept, contentType=content_type
        )
        response_body = json.loads(response["body"].read())
        original_embeddings.append(response_body.get("embedding"))
    original_embeddings = np.array(original_embeddings)

    summarized_embeddings = []
    for str in summarized_sentences:
        body = json.dumps({"inputText": str})
        response = bedrock_client.invoke_model(
            body=body, modelId=model_id, accept=accept, contentType=content_type
        )
        response_body = json.loads(response["body"].read())
        summarized_embeddings.append(response_body.get("embedding"))
    summarized_embeddings = np.array(summarized_embeddings)

    similarity_matrix = np_cosine_similarity(summarized_embeddings, original_embeddings)
    best_matching_indices = []
    len_summarized_sentences = len(summarized_sentences)
    len_original_sentences = len(original_sentences)

    # Find the best matching sentences.
    dp = np.zeros([len_summarized_sentences, len_original_sentences], dtype=float)
    for i in range(0, len_summarized_sentences):
        for j in range(0, len_original_sentences):
            if i == 0:
                dp[i][j] = similarity_matrix[i][j]
            else:
                max_score = -1
                for k in range(0, j):
                    if similarity_matrix[i][j] > 0 and dp[i - 1][k] > 0:
                        max_score = max(
                            max_score, similarity_matrix[i][j] + dp[i - 1][k]
                        )
                dp[i][j] = max_score

    j = len_original_sentences

    for i in range(min(len_original_sentences, len_summarized_sentences) - 1, -1, -1):
        arr = dp[i][:j]
        idx = np.argmax(arr)
        best_matching_indices.append(idx)
        j = idx
    best_matching_indices.reverse()

    ignored_indices = set()

    return summarized_sentences, durations, best_matching_indices, ignored_indices


def get_frames(
    bucket_transcripts,
    original_sentences,
    endTimes,
    summarized_sentences,
    durations,
    best_matching_indices,
    ignored_indices,
    intro_time,
    taskId,
):
    timecodes = [[0, intro_time]]
    for i in range(min(len(original_sentences), len(summarized_sentences))):
        if i in ignored_indices:
            continue
        startTime, endTime = get_timecodes(
            best_matching_indices,
            i,
            endTimes,
            durations[i],
            timecodes,
        )
        timecodes.append([startTime, endTime])
    creditTime = endTime + 3500
    timecodes.append([endTime, creditTime])
    timecodes_text = ""
    for timecode in timecodes:
        timecodes_text += (
            milliseconds_to_time(timecode[0])
            + ","
            + milliseconds_to_time(timecode[1])
            + "\n"
        )
    s3_client.put_object(
        Body=timecodes_text, Bucket=bucket_transcripts, Key=taskId + ".dat"
    )


def create_subtitle_summary(
    bucket_transcripts,
    original_sentences,
    summarized_sentences,
    durations,
    ignored_indices,
    intro_time,
    taskId,
):
    subtitle_summary = ""
    start = intro_time

    def split_long_lines(text, max_line_length):
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + len(current_line) > max_line_length:
                lines.append(" ".join(current_line))
                current_line = []
                current_length = 0
            current_line.append(word)
            current_length += len(word) + 1

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    for i in range(min(len(original_sentences), len(summarized_sentences))):
        if i in ignored_indices:
            continue
        end = start + durations[i]
        subtitle_summary += f"{i+1}\n"
        subtitle_summary += f"{milliseconds_to_subtitleTimeFormat(start)} --> {milliseconds_to_subtitleTimeFormat(end)}\n"
        sentence_lines = split_long_lines(summarized_sentences[i], 90)
        for line in sentence_lines:
            subtitle_summary += f"{line}\n"
        subtitle_summary += "\n"
        start = end
    s3_client.put_object(
        Body=subtitle_summary, Bucket=bucket_transcripts, Key=taskId + "-summary.srt"
    )


def get_timecodes(best_matching_indices, idx, endTimes, duration, timecodes):
    best_matching_idx = best_matching_indices[idx]
    startTime = int(endTimes[best_matching_idx]) - duration
    carry = max(0, timecodes[len(timecodes) - 1][1] - startTime)
    startTime += carry
    endTime = int(endTimes[best_matching_idx]) + carry
    return startTime, endTime


def get_subtitle(bucket_transcripts, subtitle_filename):
    subtitle = (
        s3_client.get_object(Bucket=bucket_transcripts, Key=subtitle_filename)["Body"]
        .read()
        .decode("utf-8-sig")
    )
    return subtitle


def get_polly_ssml(bucket_audio, fullpath):
    fullpath = fullpath.replace("s3://", "").split("/")
    polly_ssml_filepath = "/".join(fullpath[1:])
    polly_ssml_filename = os.path.basename(polly_ssml_filepath)
    polly_ssml = (
        s3_client.get_object(Bucket=bucket_audio, Key=polly_ssml_filename)["Body"]
        .read()
        .decode("utf-8-sig")
    )
    return polly_ssml


def get_intro(bucket_transcripts, transcribe_json_filename):
    data = (
        s3_client.get_object(Bucket=bucket_transcripts, Key=transcribe_json_filename)[
            "Body"
        ]
        .read()
        .decode("utf-8-sig")
    )
    data = json.loads(data)
    first_item = data["results"]["items"][0]
    start_time = float(first_item["start_time"]) * 1000  # ms
    return start_time


def generate_polly_audio(bucket_audio, taskId, voiceId, intro_time, taskToken):
    summarized_text = (
        s3_client.get_object(
            Bucket=os.environ["bucket_transcripts"], Key=taskId + ".txt"
        )["Body"]
        .read()
        .decode("utf-8-sig")
    )
    escaped_summarized_text = (
        summarized_text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    ssml = "<speak>\n"
    while intro_time > 10000:  # maximum break time in Polly is 10s
        ssml += '<break time = "' + str(intro_time) + 'ms"/>'
        intro_time -= 10000
    ssml += '<break time = "' + str(intro_time) + 'ms"/>'
    ssml += escaped_summarized_text
    ssml += "</speak>"
    pollyAudioResponse = create_polly_audio_task(ssml, bucket_audio, voiceId)
    add_polly_taskid(
        taskId,
        os.environ["vsh_dynamodb_table"],
        pollyAudioResponse["SynthesisTask"]["TaskId"],
        taskToken,
    )


def create_polly_audio_task(text, bucket_audio, voiceId):
    response = polly_client.start_speech_synthesis_task(
        Engine="neural",
        OutputFormat="mp3",
        OutputS3BucketName=bucket_audio,
        Text=text,
        TextType="ssml",
        SnsTopicArn=os.environ["SNSTopic"],
        VoiceId=voiceId,
    )

    return response


def add_polly_taskid(taskId, dynamodb_table, polly_task_id, sf_task_token):
    table = dynamodb_client.Table(dynamodb_table)
    ttl = str(int(time.time() + 3600))
    dynamodbResponse = table.update_item(
        Key={"TaskId": taskId},
        UpdateExpression="SET PollyTaskId = :value1, LambdaPollyTaskToken = :value2",
        ExpressionAttributeValues={":value1": polly_task_id, ":value2": sf_task_token},
    )


def remove_trademark(text, target):
    return text[: -len(target)] if text.endswith(target) else text


def milliseconds_to_time(ms, frame_rate=24):
    return "{:02d}:{:02d}:{:02d}:{:02d}".format(
        int((ms // 3600000) % 24),  # hours
        int((ms // 60000) % 60),  # minutes
        int((ms // 1000) % 60),  # seconds
        # fractions of a second (assuming 24 fps)
        int((ms % 1000) * frame_rate / 1000),
    )


def milliseconds_to_subtitleTimeFormat(ms):
    return "{:02d}:{:02d}:{:02d},{:03d}".format(
        int((ms // 3600000) % 24),  # hours
        int((ms // 60000) % 60),  # minutes
        int((ms // 1000) % 60),  # seconds
        int(ms % 1000),  # milliseconds
    )


def srt_to_arrays(s):
    sentences = [line.strip() for line in re.findall(r"\d+\n.*?\n(.*?)\n", s)]

    def get_time(s):
        return re.findall(r"\d{2}:\d{2}:\d{2},\d{3}", s)

    startTimes = get_time(s)[::2]
    endTimes = get_time(s)[1::2]
    startTimes_ms = [time_to_ms(time) for time in startTimes]
    endTimes_ms = [time_to_ms(time) for time in endTimes]

    filtered_sentences = []
    filtered_startTimes_ms = []
    filtered_endTimes_ms = []

    startTime_ms = -1
    endTime_ms = -1
    sentence = ""
    for i in range(len(sentences)):
        if startTime_ms == -1:
            startTime_ms = startTimes_ms[i]
        sentence += " " + sentences[i]
        if (
            sentences[i].endswith(".")
            or sentences[i].endswith("?")
            or sentences[i].endswith("!")
            or i == len(sentences) - 1
        ):
            endTime_ms = endTimes_ms[i]
            filtered_sentences.append(sentence)
            filtered_startTimes_ms.append(startTime_ms)
            filtered_endTimes_ms.append(endTime_ms)
            startTime_ms = -1
            endTime_ms = -1
            sentence = ""

    return filtered_sentences, filtered_startTimes_ms, filtered_endTimes_ms


def time_to_ms(time_str):
    h, m, s, ms = re.split(":|,", time_str)
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)


def np_cosine_similarity(summarized_embeddings, original_embeddings):
    dot_products = np.dot(summarized_embeddings, original_embeddings.T)
    summarized_norms = np.linalg.norm(summarized_embeddings, axis=1)
    original_norms = np.linalg.norm(original_embeddings, axis=1)

    similarity_matrix = (
        dot_products / summarized_norms[:, None] / original_norms[None, :]
    )

    return similarity_matrix
