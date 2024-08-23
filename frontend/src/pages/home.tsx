import React from "react";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Header from "@cloudscape-design/components/header";
import Container from "@cloudscape-design/components/container";
import Link from "@cloudscape-design/components/link";
import HelpPanel from "@cloudscape-design/components/help-panel";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Grid from "@cloudscape-design/components/grid";
import TextContent from "@cloudscape-design/components/text-content";
import Button from "@cloudscape-design/components/button";
import { Amplify } from "aws-amplify";
import { Authenticator } from "@aws-amplify/ui-react";
import { useAuthenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import "../styles.css";

const Home = () => {
  // console.log(import.meta.env);
  return (
    <ContentLayout
      header={
        <Grid
          gridDefinition={[
            { colspan: { default: 4, xxs: 8 } },
            { colspan: { default: 8, xxs: 4 } },
          ]}
        >
          <div>
            <Header
              variant="h1"
              description="Get a summary of videos to get the gist without having to watch the full content."
            >
              AWS Video Summarization Hub
            </Header>
          </div>
          <div style={{ marginTop: "-30px" }}>
            <Container
              header={<Header variant="h2">Get started with AWS VSH</Header>}
            >
              <SpaceBetween direction="vertical" size="l">
                <TextContent>
                  <p>
                    Upload your video to create new AWS Video Summarization task
                    with your desired configurations.
                  </p>
                </TextContent>
                <Button variant="primary" href="/vsh">
                  Create new task
                </Button>
              </SpaceBetween>
            </Container>
          </div>
        </Grid>
      }
    >
      <SpaceBetween size="l">
        <Grid
          gridDefinition={[
            { colspan: { default: 4, xxs: 8 } },
            { colspan: { default: 8, xxs: 4 } },
          ]}
        >
          <div style={{ marginTop: "50px" }}>
            <SpaceBetween size="l">
              <TextContent>
                <h1>How it works</h1>
              </TextContent>
              <Container>
                <TextContent>
                  <p>
                    AWS Video Summarization Hub (AWS VSH) is a tool that enables
                    users to ingest, process and summarize videos to short clips
                    with narrative audio in a few clicks.
                  </p>

                  <p>
                    Videos such as documentary, training videos, movies are
                    summarized with voice over in different languages.
                  </p>
                </TextContent>
              </Container>

              <Container
                header={
                  <Header variant="h2">Frequently Asked Questions</Header>
                }
              >
                <TextContent>
                  <p>
                    <strong>
                      What are the languages that are supported by AWS Video
                      Summarization Hub?
                    </strong>
                  </p>
                  <p>
                    AWS Video Summarization Hub currently offers support English
                    videos. More non-English videos will be supported in the
                    future.
                  </p>

                  <p>
                    <strong>
                      What video format is required for the input?
                    </strong>
                  </p>
                  <p>
                    For the input videos, AWS Video Summarization Hub supports
                    MP4.
                  </p>
                </TextContent>
              </Container>
            </SpaceBetween>
          </div>
          <div style={{ marginTop: "50px" }}>
            <Container header={<Header variant="h2">More Resources</Header>}>
              <TextContent>
                <Link external href="">
                  External URL
                </Link>
                <hr />
                <Link href="">Email</Link>
              </TextContent>
            </Container>
          </div>
        </Grid>
      </SpaceBetween>
    </ContentLayout>
  );
};

export default Home;
