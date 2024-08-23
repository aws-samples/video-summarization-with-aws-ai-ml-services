# Video Summarization with AWS AI/ML Services

Publishers and broadcasters can leverage short-form video across social media platforms such as Facebook, Instagram, and TikTok to attract new audiences and create additional revenue opportunities. However, generating video summaries from original content is a manual and time-consuming process due to challenges like understanding complex content, maintaining coherence, diverse video types, and lack of scalability when dealing with a large volume of videos.

Video Summarization solution allows users to automatically convert long-form videos into short-form videos with voice narrations using [Amazon Bedrock](https://aws.amazon.com/bedrock/), [Amazon Transcribe](https://aws.amazon.com/transcribe/), [Amazon Polly](https://aws.amazon.com/polly/) and [AWS Elemental MediaConvert](https://aws.amazon.com/mediaconvert/).

## Solution overview

![Architecture diagram - Video Summarization](assets/video-summarization-architecture.png?raw=true "Architecture diagram - Video Summarization")

These following steps talk through the sequence of actions that enable video summarization with AWS AI/ML services.

1. [Amazon Simple Storage Service (Amazon S3)](https://aws.amazon.com/s3/) hosts a static website for the video summarization workload, served by an [Amazon CloudFront](https://aws.amazon.com/cloudfront/) distribution. [Amazon Cognito](https://aws.amazon.com/cognito/) provides customer identity and sign-in functionality to the web application.
2. [Amazon S3](https://aws.amazon.com/s3/) stores the source videos which are uploaded through [Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html).
3. To perform a video summarization, make an API call to [Amazon API Gateway](https://aws.amazon.com/api-gateway/) that invokes an [AWS Lambda](https://aws.amazon.com/lambda/) function to put the request into an [Amazon Simple Queue Service (Amazon SQS)](https://aws.amazon.com/sqs/) queue. New messages added to the queue are processed by a Lambda function that executes a new [AWS Step Functions](https://aws.amazon.com/step-functions/) workflow.
4. [Amazon Transcribe](https://aws.amazon.com/transcribe/) converts the speech in the source video into text, generating an output subtitle file containing the transcript and timestamps.
5. [Amazon Bedrock](https://aws.amazon.com/bedrock/) foundation model endpoint summarizes the text, retaining the story from the original video but in shorter form.
6. [Amazon Polly](https://aws.amazon.com/polly/) generates a voice narration. Leverage Amazon Bedrock text embedding model endpoint to pair each sentence in the summarized text with its corresponding sentences in the original subtitle file by comparing cosine similarity of the text embeddings. The output is the most relevant video segments and their timestamps.
7. [AWS Elemental MediaConvert](https://aws.amazon.com/mediaconvert/) transcodes the final video output using the original video input clipping timestamps. It inserts the voice narration generated from Amazon Polly, with optional background music of your preference.
8. Amazon S3 stores the output video that offers durable, highly available and scalable data storage at low cost.
9. [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) tables store profiling and task metadata. This helps you keep track of the tasks’ status and other relevant information.
10. [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [Amazon EventBridge](https://aws.amazon.com/eventbridge/) monitor in near real-time every component, and can be used to integrate this workflow into other systems.

For further information, please refer to the links below:

**AWS Blog:** [Video summarization with AWS artificial intelligence (AI) and machine learning (ML) services](https://aws.amazon.com/blogs/media/video-summarization-with-aws-artificial-intelligence-ai-and-machine-learning-ml-services/)

**AWS Solution Library:** [Guidance for Video Summarization using Amazon SageMaker/Amazon Bedrock and AI Services](https://aws.amazon.com/solutions/guidance/video-summarization-using-amazon-sagemaker-and-ai-services/)

## Pre-requisites

- SAM CLI

  The solution uses [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) to provision and manage infrastructure.

- Node

  The front end for this solution is a React/TypeScript web application that can be run locally using Node

- npm

  The installation of the packages required to run the web application locally, or build it for remote deployment, require npm.

- Docker

  This solution has been built and tested using SAM CLI in conjunction with [Docker Desktop](https://www.docker.com/products/docker-desktop/) to make the build process as smooth as possible. It is possible to build and deploy this solution without Docker but we recommend using Docker as it reduces the number of local dependancies needed.
  Note that the npm `deploy` script described below requires Docker to be installed.

## Amazon Bedrock requirements

**Base Models Access**

If you are looking to interact with models from Amazon Bedrock, you need to [request access to the base models in one of the regions where Amazon Bedrock is available](https://console.aws.amazon.com/bedrock/home?#/modelaccess). Make sure to read and accept models' end-user license agreements or EULA.

Note:

- You can deploy the solution to a different region from where you requested Base Model access.
- While the Base Model access approval is instant, it might take several minutes to get access and see the list of models in the console.

## Deployment

This deployment is currently set up to deploy into the **us-east-1** region. Please check Amazon Bedrock region availability and update the `infrastructure/samconfig.toml` file to reflect your desired region.

### Environment setup

1. Clone the repository

```bash
git clone git@ssh.gitlab.aws.dev:vshhuynh/video-summarization.git
```

2. Move into the cloned repository

```bash
cd video-summarization
```

3. Start the deployment

```bash
cd frontend
npm install
npm run deploy
```

The deployment can take approximately 5-10 minutes.

### Create login details for the web application

The authenication is managed by Amazon Cognito. You will need to create a new user to be able to login.

### Login to your new web application

Once complete, the CLI output will show a value for the CloudFront URL to be able to view the web application, e.g. https://d123abc.cloudfront.net/

### User Interface

![UI](assets/video-summarization-ui.gif "Video Summarization UI")

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE.txt) file.
