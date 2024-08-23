import React, { useState, useEffect, useRef } from "react";
import Button from "@cloudscape-design/components/button";
import Form from "@cloudscape-design/components/form";
import Header from "@cloudscape-design/components/header";
import HelpPanel from "@cloudscape-design/components/help-panel";
import SpaceBetween from "@cloudscape-design/components/space-between";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Container from "@cloudscape-design/components/container";
import FormField from "@cloudscape-design/components/form-field";
import Tiles from "@cloudscape-design/components/tiles";
import Select from "@cloudscape-design/components/select";
import ProgressBar from "@cloudscape-design/components/progress-bar";
import Table from "@cloudscape-design/components/table";
import axios from "axios";
import { OptionDefinition } from "@cloudscape-design/components/internal/components/option/interfaces";
import Alert from "@cloudscape-design/components/alert";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import { Auth } from "aws-amplify";
import { Authenticator } from "@aws-amplify/ui-react";
import { useAuthenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import "../styles.css";
import {
  AWS_API_URL,
  AWS_REGION,
  AWS_USER_POOL_ID,
  AWS_USER_POOL_WEB_CLIENT_ID,
} from "../constants";

const languages = [
  { value: "yue-CN", label: "Chinese (Cantonese)" },
  { value: "cmn-CN", label: "Chinese (Mandarin)" },
  { value: "en-US", label: "English" },
  { value: "fr-FR", label: "French" },
  { value: "de-DE", label: "German" },
  { value: "it-IT", label: "Italian" },
  { value: "ja-JP", label: "Japansese" },
  { value: "ko-KR", label: "Korean" },
  { value: "pl-PL", label: "Polish" },
  { value: "pt-BR", label: "Portuguese (LATAM)" },
  { value: "es-ES", label: "Spanish" },
  { value: "es-MX", label: "Spanish (LATAM)" },
];

const voices: Array<{ value: string; label: string }> = [];
var video: File | undefined;
var language: String | undefined;
var gender: String | undefined;
var voiceId: String | undefined;

interface TableData {
  taskId: string;
  taskStatus: string;
  startTime: string;
  endTime: string;
  taskInputFilename: string;
  taskInputUrl: string;
  pollyVoice: string;
  taskOutput: string;
  taskType: string;
}
var taskIds: string[] = [];
var taskStatuses: string[] = [];
var startTimes: string[] = [];
var endTimes: string[] = [];
var taskInputFilenames: string[] = [];
var taskInputUrls: string[] = [];
var pollyVoices: string[] = [];
var taskOutputs: string[] = [];
var taskTypes: string[] = [];

const getAuthToken = async () => {
  try {
    const session = await Auth.currentSession();
    return session.getIdToken().getJwtToken();
  } catch (error) {
    console.error("Error getting auth token:", error);
    return null;
  }
};

const authenticatedAxios = axios.create();
authenticatedAxios.interceptors.request.use(
  async (config) => {
    const token = await getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

const Vsh = () => {
  const { user, signOut } = useAuthenticator((context) => [context.user]);

  const [selectedLanguage, setSelectedLanguage] = useState(languages[2]);
  const [selectedGender, setSelectedGender] = useState("male");
  const [selectedVoice, setSelectedVoice] = useState<OptionDefinition | null>(
    null
  );

  const [videoFile, setVideoFile] = useState<File | null>(null);
  const videoInput = useRef<HTMLInputElement>(null);
  const [isVideoStatusVisible, setIsVideoStatusVisible] = useState(false);

  const userId = user?.username;

  const handleVideoFileInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setVideoFile(file);
      setIsVideoStatusVisible(true);
      const videoPlayer = document.getElementById(
        "videoPlayer"
      ) as HTMLVideoElement;
      if (videoPlayer) {
        videoPlayer.src = URL.createObjectURL(file);
        videoPlayer.load(); // Load the new video source
      }
    } else {
      setVideoFile(null);
      setIsVideoStatusVisible(false);
    }
    video = event.target.files?.[0];
  };
  const triggerVideoFileInput = () => {
    if (videoInput.current) {
      videoInput.current.click();
    }
  };

  const [progress, setProgress] = useState(0);
  const [progressInfo, setProgressInfo] = useState("");
  const [selectedItems, setSelectedItems] = useState<TableData[]>([]);
  const [tableData, setTableData] = useState<TableData[]>([]);
  const addItem = (item: TableData) => {
    setTableData((prevTableData) => [item, ...prevTableData]);
  };

  const [isSubmitDisabled, setIsSubmitDisabled] = useState(false);
  const handleSubmitClick = () => {
    if (userId) {
      if (video == null) {
        setShowAlert(true);
        return;
      }
      setIsSubmitDisabled(true);
      setIsRefreshDisabled(true);
      setShowAlert(false);
      uploadVideo(
        userId,
        setProgress,
        setProgressInfo,
        addItem,
        setIsSubmitDisabled,
        setIsRefreshDisabled
      );
    }
  };

  const [isRefreshDisabled, setIsRefreshDisabled] = useState(false);
  const [isTableLoading, setIsTableLoading] = useState(false);
  const [downloadText, setDownloadText] = useState("");

  const handleRefreshClick = () => {
    setIsRefreshDisabled(true);
    setIsTableLoading(true);
    const promises = taskIds.map((taskId, i) => {
      if (taskStatuses[i] === "Complete") return;
      return authenticatedAxios
        .get(AWS_API_URL + "/gettaskstatus?taskId=" + taskId)
        .then((response) => {
          taskStatuses[i] = response.data["status"];
          endTimes[i] = response.data["endTime"];
          taskOutputs[i] = response.data["outputUrl"];
          if (taskStatuses[i] === "Complete") {
            setDownloadText("Download");
          }
          if (response.status == 200) {
          }
        })
        .catch((error) => {
          setIsRefreshDisabled(false);
          setIsTableLoading(false);
          console.error(error);
        });
    });
    Promise.all(promises)
      .then(() => {
        const updatedTableData = tableData.map((item, index) => {
          (item.taskStatus = taskStatuses[index]),
            (item.endTime = endTimes[index]),
            (item.taskOutput = taskOutputs[index]);
          return item;
        });
        setTableData(updatedTableData);
        setIsRefreshDisabled(false);
        setIsTableLoading(false);
      })
      .catch((error) => {
        console.error(error);
        setIsRefreshDisabled(false);
        setIsTableLoading(false);
      });
  };

  const [showAlert, setShowAlert] = useState(false);

  useEffect(() => {
    if (userId) {
      language = selectedLanguage.value;
      gender = selectedGender;
      getVoices(setSelectedVoice);
      retrieveAllTasks(userId, addItem);
    }
  }, [userId]);

  return (
    <ContentLayout
      header={
        <Header variant="h1" description="Upload video to create a new task">
          Create new AWS Video Summarization
        </Header>
      }
    >
      <SpaceBetween size="l">
        <form onSubmit={(event) => event.preventDefault()}>
          <Form
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  onClick={handleSubmitClick}
                  variant="primary"
                  disabled={isSubmitDisabled}
                >
                  Submit
                </Button>
              </SpaceBetween>
            }
          >
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                marginBottom: "10px",
              }}
            >
              <div style={{ width: "55%" }}>
                <Container
                  className="customised-container"
                  header={
                    <Header
                      variant="h2"
                      description="Upload original video in MP4 format"
                      actions={
                        isVideoStatusVisible && (
                          <StatusIndicator></StatusIndicator>
                        )
                      }
                    >
                      Video
                    </Header>
                  }
                >
                  <div style={{ display: "flex", flexDirection: "row" }}>
                    <div style={{ width: "50%", marginRight: "30px" }}>
                      <SpaceBetween direction="vertical" size="s">
                        <Button
                          href=""
                          iconName="upload"
                          onClick={triggerVideoFileInput}
                          disabled={false}
                        >
                          Choose Video File
                        </Button>
                        <div>
                          <input
                            type="file"
                            id="video"
                            ref={videoInput}
                            onChange={handleVideoFileInput}
                            style={{ display: "none" }}
                            accept="video/mp4"
                          />
                          {videoFile && (
                            <p>
                              {videoFile.name.length <= 35
                                ? videoFile.name
                                : videoFile.name.slice(0, 20) +
                                  "..." +
                                  videoFile.name.slice(-12)}
                            </p>
                          )}
                          <button
                            type="submit"
                            style={{ display: "none" }}
                          ></button>
                        </div>
                        <div style={{ width: "1%" }} />
                      </SpaceBetween>
                    </div>
                    <div
                      style={{
                        marginTop: "-5%",
                        marginLeft: "-5%",
                        overflow: "hidden",
                      }}
                    >
                      <video
                        id="videoPlayer"
                        width="320"
                        height="180"
                        controls
                        preload="none"
                        style={{ borderRadius: "10px" }}
                      ></video>
                    </div>
                  </div>
                </Container>
              </div>

              <div style={{ width: "1%" }} />

              <div style={{ width: "45%" }}>
                <Container
                  header={<Header variant="h2">Narrative Voice</Header>}
                >
                  <SpaceBetween direction="vertical" size="l">
                    <FormField label="Select a language">
                      <Select
                        selectedOption={selectedLanguage}
                        onChange={({ detail }) => {
                          if (detail.selectedOption) {
                            setSelectedLanguage({
                              value: detail.selectedOption.value!,
                              label: detail.selectedOption.label!,
                            });
                          }
                          language = detail.selectedOption.value;
                          getVoices(setSelectedVoice);
                        }}
                        options={languages}
                        selectedAriaLabel="Selected"
                      />
                    </FormField>
                    <FormField label="Voice gender" stretch={true}>
                      <Tiles
                        items={[
                          {
                            value: "male",
                            label: "Male",
                          },
                          {
                            value: "female",
                            label: "Female",
                          },
                        ]}
                        value={selectedGender}
                        onChange={(e) => {
                          setSelectedGender(e.detail.value);
                          gender = e.detail.value;
                          getVoices(setSelectedVoice);
                        }}
                      />
                    </FormField>
                    <FormField label="List of available voices">
                      <Select
                        selectedOption={selectedVoice}
                        onChange={({ detail }) => {
                          setSelectedVoice(detail.selectedOption);
                          voiceId = detail.selectedOption.value;
                        }}
                        options={voices}
                        selectedAriaLabel="Selected"
                      />
                    </FormField>
                  </SpaceBetween>
                </Container>
              </div>
            </div>

            <Alert
              statusIconAriaLabel="Error"
              type="error"
              header="Your task could not be created"
              visible={showAlert}
            >
              Upload a new video before creating a Video Summarization task.
            </Alert>
          </Form>
        </form>
        <Container
          header={
            <Header
              variant="h2"
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    iconName="refresh"
                    variant="normal"
                    onClick={handleRefreshClick}
                    disabled={isRefreshDisabled}
                  />
                </SpaceBetween>
              }
            >
              Task Status
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="xl">
            <ProgressBar
              value={progress}
              additionalInfo={progressInfo}
              //description="Description"
              label="Create new task"
            />

            <Table
              onSelectionChange={({ detail }) =>
                setSelectedItems(detail.selectedItems)
              }
              selectedItems={selectedItems}
              ariaLabels={{
                selectionGroupLabel: "Items selection",
                allItemsSelectionLabel: ({ selectedItems }) =>
                  `${selectedItems.length} ${
                    selectedItems.length === 1 ? "item" : "items"
                  } selected`,
                itemSelectionLabel: ({ selectedItems }, item) => {
                  const isItemSelected = selectedItems.filter(
                    (i) => i.taskId === item.taskId
                  ).length;
                  return `${item.taskId} is ${
                    isItemSelected ? "" : "not"
                  } selected`;
                },
              }}
              columnDefinitions={[
                {
                  id: "taskInputUrl",
                  header: "Original Video",
                  cell: (e) => (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                      }}
                    >
                      <video
                        width="320"
                        height="180"
                        controls
                        preload="auto"
                        style={{ borderRadius: "10px" }}
                      >
                        <source src={e.taskInputUrl} type="video/mp4" />
                      </video>
                      <p>
                        {(() => {
                          const videoFileName =
                            e.taskInputFilename.split("/").pop() ||
                            e.taskInputFilename;

                          return videoFileName.length <= 35
                            ? videoFileName
                            : videoFileName.slice(0, 20) +
                                "..." +
                                videoFileName.slice(-12);
                        })()}
                      </p>
                    </div>
                  ),
                  minWidth: 70,
                },
                {
                  id: "pollyVoice",
                  header: "Voice",
                  cell: (e) => e.pollyVoice,
                },
                {
                  id: "taskStatus",
                  header: "Status",
                  cell: (e) => e.taskStatus,
                },
                {
                  id: "startTime",
                  header: "Started",
                  cell: (e) => (
                    <p style={{ textAlign: "left" }}>
                      {e.startTime.split(" ")[1]}
                      <br />
                      {e.startTime.split(" ")[0]}
                    </p>
                  ),
                },
                {
                  id: "endTime",
                  header: "End Time",
                  cell: (e) => (
                    <p style={{ textAlign: "left" }}>
                      {e.endTime.split(" ")[1]}
                      <br />
                      {e.endTime.split(" ")[0]}
                    </p>
                  ),
                },
                {
                  id: "taskOutput",
                  header: "Short-Form Video",
                  cell: (e) =>
                    // <a href={e.taskOutput} target="_blank" download={e.taskId + ".mp4"}>{e.taskOutput || ''}</a>
                    e.taskOutput === "-" || e.taskOutput === "" ? (
                      <p></p>
                    ) : e.taskType == "Validated" ? (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                        }}
                      >
                        <video
                          width="320"
                          height="180"
                          controls
                          preload="auto"
                          style={{ borderRadius: "10px" }}
                        >
                          <source src={e.taskOutput} type="video/mp4" />
                        </video>
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "row",
                            alignItems: "center",
                          }}
                        >
                          <StatusIndicator colorOverride="blue"></StatusIndicator>
                          <p> {e.taskInputFilename}</p>
                        </div>
                      </div>
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                        }}
                      >
                        <video
                          width="320"
                          height="180"
                          controls
                          preload="auto"
                          style={{ borderRadius: "10px" }}
                        >
                          <source src={e.taskOutput} type="video/mp4" />
                        </video>
                        <p>
                          {(() => {
                            const videoFileName =
                              e.taskInputFilename.split("/").pop() ||
                              e.taskInputFilename;

                            return videoFileName.length <= 35
                              ? videoFileName
                              : videoFileName.slice(0, 20) +
                                  "..." +
                                  videoFileName.slice(-12);
                          })()}
                        </p>
                      </div>
                    ),
                  minWidth: 200,
                  maxWidth: 350,
                },
              ]}
              items={tableData}
              variant="embedded"
              loading={isTableLoading}
              loadingText=""
              selectionType="multi"
              trackBy="taskId"
            />
          </SpaceBetween>
        </Container>
      </SpaceBetween>
    </ContentLayout>
  );
};

export default Vsh;

function getVoices(setSelectedVoice: (x: OptionDefinition) => void) {
  voices.length = 0;
  const fetchData = async () => {
    const response = await authenticatedAxios
      .get(
        AWS_API_URL + "/getvoices?language=" + language + "&gender=" + gender
      )
      .then((response) => {
        if (response.status == 200) {
          if (response.data["Voices"].length > 0) {
            const sortedVoices = [...response.data["Voices"]].sort((a, b) =>
              a.Id.localeCompare(b.Id)
            );
            for (var i = 0; i < sortedVoices.length; i++) {
              var voice = sortedVoices[i];
              voices.push({ value: voice["Id"], label: voice["Id"] });
            }
          } else {
            voices.push({
              value: "No voice available",
              label: "No voice available",
            });
          }
          setSelectedVoice(voices[0]);
          voiceId = voices[0].value;
        }
      })
      .catch((error) => {
        console.error(error);
      });
  };
  fetchData();
}

function uploadVideo(
  userId: string,
  setProgress: {
    (value: React.SetStateAction<number>): void;
    (arg0: number): void;
  },
  setProgressInfo: {
    (value: React.SetStateAction<string>): void;
    (arg0: string): void;
  },
  addItem: (item: TableData) => void,
  setIsSubmitDisabled: React.Dispatch<React.SetStateAction<boolean>>,
  setIsRefreshDisabled: React.Dispatch<React.SetStateAction<boolean>>
) {
  setProgress(0);
  setProgressInfo("Uploading video...");
  const fetchData = async () => {
    if (!video) return;
    const response = await authenticatedAxios
      .get(
        AWS_API_URL +
          "/presignedurl_video?type=post&userId=" +
          userId +
          "&object_name=" +
          video.name
      )
      .then((response) => {
        if (response.status == 200) {
          var presignedUrl = response.data.url;
          var fields = response.data.fields;
          var key = fields["key"];
          var AWSAccessKeyId = fields["AWSAccessKeyId"];
          var xAmzSecurityToken = fields["x-amz-security-token"];
          var policy = fields["policy"];
          var signature = fields["signature"];

          var formData = new FormData();
          formData.append("key", key);
          formData.append("AWSAccessKeyId", AWSAccessKeyId);
          formData.append("x-amz-security-token", xAmzSecurityToken);
          formData.append("policy", policy);
          formData.append("signature", signature);
          if (video) formData.append("file", video);

          axios
            .post(presignedUrl, formData, {
              onUploadProgress: (progressEvent) => {
                if (!progressEvent.total) return;
                setProgress((progressEvent.loaded / progressEvent.total) * 100);
              },
            })
            .then((response) => {
              if ((response.status = 200)) {
                startStepFunctionExecution(
                  userId,
                  key,
                  setProgress,
                  setProgressInfo,
                  addItem,
                  setIsSubmitDisabled,
                  setIsRefreshDisabled
                );
              }
            })
            .catch((error) => {
              console.error(error);
            });
        }
      })
      .catch((error) => {
        console.error(error);
      });
  };
  fetchData();
}

function startStepFunctionExecution(
  userId: String,
  video_name: String,
  setProgress: {
    (value: React.SetStateAction<number>): void;
    (arg0: number): void;
    (arg0: number): void;
    (arg0: number): void;
  },
  setProgressInfo: {
    (value: React.SetStateAction<string>): void;
    (arg0: string): void;
    (arg0: string): void;
    (arg0: string): void;
  },
  addItem: (item: TableData) => void,
  setIsSubmitDisabled: React.Dispatch<React.SetStateAction<boolean>>,
  setIsRefreshDisabled: React.Dispatch<React.SetStateAction<boolean>>
) {
  setProgress(Math.floor(Math.random() * (90 - 70 + 1)) + 70);
  setProgressInfo("Processing files...");
  const fetchData = async () => {
    if (!video) return;
    const response = await authenticatedAxios
      .get(
        AWS_API_URL +
          "/stepfunction?userId=" +
          userId +
          "&video_name=" +
          video_name +
          "&language=" +
          language +
          "&voiceId=" +
          voiceId +
          "&gender=" +
          gender
      )
      .then((response) => {
        if (response.status == 200) {
          setProgress(100);
          setProgressInfo("Task is successfully created.");
          taskIds.unshift(response.data["taskId"]);
          taskStatuses.unshift("Running");
          startTimes.unshift(response.data["started"]);
          endTimes.unshift("");
          taskInputFilenames.unshift(response.data["inputFilename"]);
          taskInputUrls.unshift(response.data["inputUrl"]);
          pollyVoices.unshift(response.data["pollyVoice"]);
          taskOutputs.unshift("");
          taskTypes.unshift(response.data["taskType"]);
          const item = {
            taskId: response.data["taskId"],
            taskStatus: "Running",
            startTime: response.data["started"],
            endTime: "",
            taskInputFilename: response.data["inputFilename"],
            taskInputUrl: response.data["inputUrl"],
            pollyVoice: response.data["pollyVoice"],
            taskOutput: "",
            taskType: "",
          };
          addItem(item);
        }
        setIsSubmitDisabled(false);
        setIsRefreshDisabled(false);
      })
      .catch((error) => {
        setIsSubmitDisabled(false);
        setIsRefreshDisabled(false);
        console.error(error);
      });
  };
  fetchData();
}

function retrieveAllTasks(userId: string, addItem: (item: TableData) => void) {
  const fetchData = async () => {
    const response = await authenticatedAxios
      .get(AWS_API_URL + "/gettasks?userId=" + userId)
      .then((response) => {
        if (response.status == 200) {
          let tasks = response.data;
          tasks = tasks
            .slice()
            .sort((taskA: { started: string }, taskB: { started: string }) => {
              const startedA = taskA.started as string;
              const startedB = taskB.started as string;

              return (
                new Date(startedA).getTime() - new Date(startedB).getTime()
              );
            });
          for (let i = 0; i < tasks.length; i++) {
            taskIds.unshift(tasks[i]["taskId"]);
            taskStatuses.unshift(tasks[i]["status"]);
            startTimes.unshift(tasks[i]["started"]);
            endTimes.unshift(
              tasks[i]["endTime"] === "-" ? "" : tasks[i]["endTime"]
            );
            taskInputFilenames.unshift(tasks[i]["inputFilename"]);
            taskInputUrls.unshift(tasks[i]["inputUrl"]);
            pollyVoices.unshift(tasks[i]["pollyVoice"]);
            taskOutputs.unshift(tasks[i]["outputUrl"]);
            taskTypes.unshift(tasks[i]["taskType"]);
            let item = {
              taskId: tasks[i]["taskId"],
              taskStatus: tasks[i]["status"],
              startTime: tasks[i]["started"],
              endTime: tasks[i]["endTime"] === "-" ? "" : tasks[i]["endTime"],
              taskInputFilename: tasks[i]["inputFilename"],
              taskInputUrl: tasks[i]["inputUrl"],
              pollyVoice: tasks[i]["pollyVoice"],
              taskOutput: tasks[i]["outputUrl"],
              taskType: tasks[i]["taskType"],
            };
            addItem(item);
          }
        }
      })
      .catch((error) => {
        console.error(error);
      });
  };
  fetchData();
}
