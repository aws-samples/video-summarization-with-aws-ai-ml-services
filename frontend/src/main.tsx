// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from "react";
import ReactDOM from "react-dom/client";

import "@cloudscape-design/global-styles/index.css";

import App from "./app";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Home from "./pages/home";
import Vsh from "./pages/vsh";

const root = ReactDOM.createRoot(document.getElementById("root")!);

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: "vsh", element: <Vsh /> },
    ],
  },
]);

root.render(
  <>
    <RouterProvider router={router} />
  </>
);

/*root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);*/
