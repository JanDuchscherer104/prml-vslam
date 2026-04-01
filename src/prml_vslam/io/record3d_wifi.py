"""Browser-side Record3D Wi-Fi streaming component for the Streamlit app."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Literal, Self

import streamlit as st
from pydantic import Field

from prml_vslam.utils.base_config import BaseConfig

Record3DWiFiConnectionState = Literal["idle", "connecting", "streaming", "disconnected", "failed"]


class Record3DWiFiViewerState(BaseConfig):
    """Latest browser-visible state emitted by the Record3D Wi-Fi viewer."""

    device_address: str = ""
    """Normalized Record3D device address currently targeted by the viewer."""

    connection_state: Record3DWiFiConnectionState = "idle"
    """Current Wi-Fi/WebRTC connection state reported by the browser component."""

    error_message: str = ""
    """Current error or warning message surfaced by the browser component."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Latest JSON metadata returned by the Record3D `/metadata` endpoint."""

    show_inv_dist_std: bool = True
    """Whether the optional placeholder pane should stay visible."""

    equalize_depth_histogram: bool = False
    """Whether the browser should histogram-equalize the depth preview."""

    @classmethod
    def from_component_result(cls, result: Any) -> Self:
        """Normalize a Streamlit component result into a stable typed state."""
        defaults = cls().model_dump(mode="python")
        raw_state = dict(result) if result is not None else {}
        normalized = {
            field_name: defaults[field_name] if raw_state.get(field_name) is None else raw_state[field_name]
            for field_name in cls.model_fields
        }
        return cls.model_validate(normalized)

    def to_component_data(self) -> dict[str, Any]:
        """Return the frontend data payload used to initialize the viewer."""
        return {
            "device_address": self.device_address,
            "show_inv_dist_std": self.show_inv_dist_std,
            "equalize_depth_histogram": self.equalize_depth_histogram,
        }


RECORD3D_WIFI_COMPONENT_NAME = "prml_vslam_record3d_wifi_viewer"
RECORD3D_WIFI_COMPONENT_KEY = "record3d_wifi_viewer"
RECORD3D_WIFI_COMPONENT_HEIGHT = 760

RECORD3D_WIFI_COMPONENT_HTML = dedent(
    """
    <section class="record3d-wifi-root">
      <header class="record3d-wifi-header">
        <div>
          <p class="record3d-kicker">Record3D Wi-Fi</p>
          <h2>Live RGBD stream preview</h2>
          <p class="record3d-lede">
            Enter the device address shown in the iPhone app to preview the composite
            RGBD WebRTC stream in this browser.
          </p>
        </div>
      </header>

      <form class="record3d-controls" id="record3d-connect-form">
        <label class="record3d-label" for="record3d-device-address">Device address</label>
        <div class="record3d-input-row">
          <input
            id="record3d-device-address"
            class="record3d-input"
            type="text"
            placeholder="myiPhone.local or 192.168.1.100"
            autocomplete="off"
            spellcheck="false"
          />
          <button id="record3d-connect-button" class="record3d-button" type="submit">
            Connect
          </button>
        </div>
      </form>

      <div class="record3d-status-row">
        <span id="record3d-status-pill" class="record3d-status-pill" data-state="idle">IDLE</span>
        <span id="record3d-status-address" class="record3d-status-address">No device connected yet.</span>
      </div>

      <p id="record3d-error-message" class="record3d-error-message" hidden></p>

      <div class="record3d-view-options">
        <label class="record3d-checkbox" for="record3d-toggle-inv-dist-std">
          <input id="record3d-toggle-inv-dist-std" type="checkbox" checked />
          <span>Show <code>inv_dist_std</code> pane</span>
        </label>
        <label class="record3d-checkbox" for="record3d-toggle-depth-equalization">
          <input id="record3d-toggle-depth-equalization" type="checkbox" />
          <span>Histogram equalize depth preview</span>
        </label>
      </div>

      <video id="record3d-video-source" class="record3d-video-source" playsinline autoplay muted></video>

      <div id="record3d-frame-grid" class="record3d-frame-grid" data-show-inv-dist-std="true">
        <section class="record3d-frame-panel">
          <div class="record3d-frame-header">
            <h3>RGB</h3>
            <p>Right half of the Record3D composite Wi-Fi stream.</p>
          </div>
          <canvas id="record3d-rgb-canvas" class="record3d-frame-canvas"></canvas>
        </section>

        <section class="record3d-frame-panel">
          <div class="record3d-frame-header">
            <h3>Depth</h3>
            <p>Decoded from the left half of the composite Wi-Fi stream.</p>
          </div>
          <canvas id="record3d-depth-canvas" class="record3d-frame-canvas"></canvas>
        </section>

        <section id="record3d-inv-dist-std-panel" class="record3d-frame-panel">
          <div class="record3d-frame-header">
            <h3><code>inv_dist_std</code></h3>
            <p>Not exposed by the current Record3D Wi-Fi WebRTC stream.</p>
          </div>
          <div id="record3d-inv-dist-std-placeholder" class="record3d-frame-placeholder">
            The official Wi-Fi API exposes RGB and depth through a composite frame, but no separate
            <code>inv_dist_std</code> channel.
          </div>
        </section>
      </div>

      <section class="record3d-metadata-section">
        <div class="record3d-section-header">
          <h3>Metadata</h3>
          <p>Latest payload from the Record3D <code>/metadata</code> endpoint.</p>
        </div>
        <pre id="record3d-metadata-view" class="record3d-metadata-view">{}</pre>
      </section>
    </section>
    """
).strip()

RECORD3D_WIFI_COMPONENT_CSS = dedent(
    """
    :host {
      display: block;
      width: 100%;
      height: 100%;
    }

    .record3d-wifi-root {
      display: grid;
      gap: 1rem;
      min-height: 100%;
      color: #16202a;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }

    .record3d-wifi-header h2,
    .record3d-metadata-section h3,
    .record3d-frame-header h3 {
      margin: 0;
    }

    .record3d-kicker {
      margin: 0 0 0.3rem;
      color: #2563eb;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .record3d-lede,
    .record3d-section-header p,
    .record3d-frame-header p {
      margin: 0;
      color: #5a6875;
      line-height: 1.5;
    }

    .record3d-controls,
    .record3d-frame-panel,
    .record3d-metadata-section {
      border: 1px solid #dbe4ea;
      border-radius: 1rem;
      background: #ffffff;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
    }

    .record3d-controls {
      display: grid;
      gap: 0.45rem;
      padding: 1rem;
    }

    .record3d-label {
      font-size: 0.9rem;
      font-weight: 600;
    }

    .record3d-input-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 0.75rem;
      align-items: center;
    }

    .record3d-input {
      min-width: 0;
      padding: 0.8rem 0.95rem;
      border: 1px solid #cfd8df;
      border-radius: 0.8rem;
      background: #f8fbfd;
      color: #16202a;
      font-size: 0.98rem;
    }

    .record3d-button {
      padding: 0.8rem 1rem;
      border: none;
      border-radius: 0.8rem;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: white;
      cursor: pointer;
      font-size: 0.98rem;
      font-weight: 700;
      white-space: nowrap;
    }

    .record3d-button:disabled {
      cursor: wait;
      opacity: 0.7;
    }

    .record3d-status-row {
      display: flex;
      gap: 0.75rem;
      align-items: center;
      flex-wrap: wrap;
    }

    .record3d-status-pill {
      padding: 0.35rem 0.7rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      background: #eef2f6;
      color: #5a6875;
    }

    .record3d-status-pill[data-state="connecting"] {
      background: #fff5db;
      color: #b45309;
    }

    .record3d-status-pill[data-state="streaming"] {
      background: #dcfce7;
      color: #047857;
    }

    .record3d-status-pill[data-state="disconnected"] {
      background: #dbeafe;
      color: #1d4ed8;
    }

    .record3d-status-pill[data-state="failed"] {
      background: #fee2e2;
      color: #b91c1c;
    }

    .record3d-status-address {
      font-size: 0.95rem;
      color: #5a6875;
    }

    .record3d-error-message {
      margin: 0;
      padding: 0.8rem 0.95rem;
      border: 1px solid #fecaca;
      border-radius: 0.8rem;
      background: #fef2f2;
      color: #991b1b;
      line-height: 1.5;
    }

    .record3d-view-options {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.8rem;
    }

    .record3d-checkbox {
      display: inline-flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.95rem;
      font-weight: 500;
      color: #16202a;
    }

    .record3d-checkbox input {
      width: 1rem;
      height: 1rem;
      accent-color: #2563eb;
    }

    .record3d-video-source {
      display: none;
    }

    .record3d-frame-grid {
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .record3d-frame-grid[data-show-inv-dist-std="false"] {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .record3d-frame-panel {
      display: grid;
      gap: 0.75rem;
      min-width: 0;
      padding: 1rem;
    }

    .record3d-frame-canvas,
    .record3d-frame-placeholder {
      width: 100%;
      min-height: 16rem;
      border-radius: 0.85rem;
      border: 1px solid #dbe4ea;
      background: #f5f7fa;
    }

    .record3d-frame-canvas {
      display: block;
      aspect-ratio: 4 / 3;
      object-fit: contain;
    }

    .record3d-frame-placeholder {
      display: grid;
      place-items: center;
      padding: 1rem;
      color: #5a6875;
      line-height: 1.5;
      text-align: center;
    }

    .record3d-metadata-section {
      display: grid;
      gap: 0.6rem;
      padding: 1rem;
    }

    .record3d-section-header {
      display: grid;
      gap: 0.2rem;
    }

    .record3d-metadata-view {
      margin: 0;
      padding: 1rem;
      border-radius: 0.85rem;
      overflow-x: auto;
      background: #f8fbfd;
      color: #16202a;
      font-size: 0.88rem;
      line-height: 1.5;
    }

    @media (max-width: 720px) {
      .record3d-input-row {
        grid-template-columns: 1fr;
      }

      .record3d-button {
        width: 100%;
      }

      .record3d-frame-grid,
      .record3d-frame-grid[data-show-inv-dist-std="false"] {
        grid-template-columns: 1fr;
      }
    }
    """
).strip()

RECORD3D_WIFI_COMPONENT_JS = dedent(
    """
    export default function(component) {
      const { parentElement, setStateValue, data } = component;
      const initialData = typeof data === "string" ? JSON.parse(data) : (data || {});
      const root = parentElement;
      const ui = {
        form: root.querySelector("#record3d-connect-form"),
        input: root.querySelector("#record3d-device-address"),
        connectButton: root.querySelector("#record3d-connect-button"),
        statusPill: root.querySelector("#record3d-status-pill"),
        statusAddress: root.querySelector("#record3d-status-address"),
        errorMessage: root.querySelector("#record3d-error-message"),
        metadataView: root.querySelector("#record3d-metadata-view"),
        sourceVideo: root.querySelector("#record3d-video-source"),
        frameGrid: root.querySelector("#record3d-frame-grid"),
        rgbCanvas: root.querySelector("#record3d-rgb-canvas"),
        depthCanvas: root.querySelector("#record3d-depth-canvas"),
        invDistStdPanel: root.querySelector("#record3d-inv-dist-std-panel"),
        invDistStdToggle: root.querySelector("#record3d-toggle-inv-dist-std"),
        depthEqualizationToggle: root.querySelector("#record3d-toggle-depth-equalization"),
      };

      const publishState = (viewer) => {
        viewer.setStateValue("device_address", viewer.deviceAddress);
        viewer.setStateValue("connection_state", viewer.connectionState);
        viewer.setStateValue("error_message", viewer.errorMessage);
        viewer.setStateValue("metadata", viewer.metadata);
        viewer.setStateValue("show_inv_dist_std", viewer.showInvDistStd);
        viewer.setStateValue("equalize_depth_histogram", viewer.equalizeDepthHistogram);
      };

      const setCanvasSize = (canvas, width, height) => {
        if (canvas.width !== width || canvas.height !== height) {
          canvas.width = width;
          canvas.height = height;
        }
      };

      const clearCanvas = (context, canvas) => {
        if (context === null) {
          return;
        }
        context.clearRect(0, 0, canvas.width, canvas.height);
      };

      const rgbToHue = (red, green, blue) => {
        const normalizedRed = red / 255.0;
        const normalizedGreen = green / 255.0;
        const normalizedBlue = blue / 255.0;
        const maximum = Math.max(normalizedRed, normalizedGreen, normalizedBlue);
        const minimum = Math.min(normalizedRed, normalizedGreen, normalizedBlue);
        const delta = maximum - minimum;

        if (delta === 0) {
          return 0.0;
        }

        switch (maximum) {
          case normalizedRed:
            return (((normalizedGreen - normalizedBlue) / delta) % 6 + 6) % 6 / 6;
          case normalizedGreen:
            return (((normalizedBlue - normalizedRed) / delta) + 2) / 6;
          default:
            return (((normalizedRed - normalizedGreen) / delta) + 4) / 6;
        }
      };

      const updateFrameLayout = (viewer) => {
        ui.invDistStdToggle.checked = viewer.showInvDistStd;
        ui.depthEqualizationToggle.checked = viewer.equalizeDepthHistogram;
        ui.frameGrid.dataset.showInvDistStd = viewer.showInvDistStd ? "true" : "false";
        ui.invDistStdPanel.hidden = !viewer.showInvDistStd;
      };

      const equalizeHistogram = (intensities) => {
        const histogram = new Uint32Array(256);
        const equalized = new Uint8ClampedArray(intensities.length);

        for (let index = 0; index < intensities.length; index += 1) {
          histogram[intensities[index]] += 1;
        }

        let firstNonZeroBin = -1;
        for (let bin = 0; bin < histogram.length; bin += 1) {
          if (histogram[bin] > 0) {
            firstNonZeroBin = bin;
            break;
          }
        }

        if (firstNonZeroBin === -1) {
          return equalized;
        }

        const cumulative = new Uint32Array(256);
        let runningTotal = 0;
        for (let bin = 0; bin < histogram.length; bin += 1) {
          runningTotal += histogram[bin];
          cumulative[bin] = runningTotal;
        }

        const denominator = intensities.length - cumulative[firstNonZeroBin];
        if (denominator <= 0) {
          return intensities;
        }

        for (let index = 0; index < intensities.length; index += 1) {
          const source = intensities[index];
          equalized[index] = Math.max(
            0,
            Math.min(255, Math.round(((cumulative[source] - cumulative[firstNonZeroBin]) / denominator) * 255.0)),
          );
        }

        return equalized;
      };

      const render = (viewer) => {
        if (viewer.deviceAddress !== "" && ui.input.value !== viewer.deviceAddress) {
          ui.input.value = viewer.deviceAddress;
        }

        ui.statusPill.dataset.state = viewer.connectionState;
        ui.statusPill.textContent = viewer.connectionState.toUpperCase();
        ui.statusAddress.textContent = viewer.deviceAddress || "No device connected yet.";
        ui.connectButton.disabled = viewer.connectionState === "connecting";
        ui.connectButton.textContent = viewer.connectionState === "connecting" ? "Connecting..." : "Connect";
        ui.metadataView.textContent = JSON.stringify(viewer.metadata, null, 2);

        if (viewer.errorMessage !== "") {
          ui.errorMessage.hidden = false;
          ui.errorMessage.textContent = viewer.errorMessage;
        } else {
          ui.errorMessage.hidden = true;
          ui.errorMessage.textContent = "";
        }

        updateFrameLayout(viewer);
      };

      const stopVideoStream = () => {
        const stream = ui.sourceVideo.srcObject;
        if (stream !== null) {
          stream.getTracks().forEach((track) => track.stop());
          ui.sourceVideo.srcObject = null;
        }
      };

      const stopFrameRendering = (viewer) => {
        if (viewer.animationFrameId !== null) {
          window.cancelAnimationFrame(viewer.animationFrameId);
          viewer.animationFrameId = null;
        }

        clearCanvas(viewer.rgbContext, ui.rgbCanvas);
        clearCanvas(viewer.depthContext, ui.depthCanvas);
      };

      const renderDepthFrame = (viewer, frameWidth, frameHeight) => {
        const sourceImage = viewer.scratchContext.getImageData(0, 0, frameWidth, frameHeight);
        const depthImage = viewer.depthContext.createImageData(frameWidth, frameHeight);
        const sourcePixels = sourceImage.data;
        const targetPixels = depthImage.data;
        const intensities = new Uint8ClampedArray(frameWidth * frameHeight);

        for (let pixelOffset = 0; pixelOffset < sourcePixels.length; pixelOffset += 4) {
          const hue = rgbToHue(
            sourcePixels[pixelOffset],
            sourcePixels[pixelOffset + 1],
            sourcePixels[pixelOffset + 2],
          );
          intensities[pixelOffset / 4] = Math.max(0, Math.min(255, Math.round((1.0 - hue) * 255.0)));
        }

        const displayIntensities = viewer.equalizeDepthHistogram ? equalizeHistogram(intensities) : intensities;
        for (let pixelIndex = 0; pixelIndex < displayIntensities.length; pixelIndex += 1) {
          const intensity = displayIntensities[pixelIndex];
          const pixelOffset = pixelIndex * 4;
          targetPixels[pixelOffset] = intensity;
          targetPixels[pixelOffset + 1] = intensity;
          targetPixels[pixelOffset + 2] = intensity;
          targetPixels[pixelOffset + 3] = 255;
        }

        viewer.depthContext.putImageData(depthImage, 0, 0);
      };

      const startFrameRendering = (viewer) => {
        stopFrameRendering(viewer);

        const drawFrame = () => {
          if (!root.isConnected) {
            viewer.animationFrameId = null;
            return;
          }

          const video = ui.sourceVideo;
          if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.videoWidth >= 2 && video.videoHeight > 0) {
            const compositeWidth = video.videoWidth;
            const compositeHeight = video.videoHeight;
            const frameWidth = Math.floor(compositeWidth / 2);

            if (frameWidth > 0) {
              setCanvasSize(ui.rgbCanvas, frameWidth, compositeHeight);
              setCanvasSize(ui.depthCanvas, frameWidth, compositeHeight);
              setCanvasSize(viewer.scratchCanvas, compositeWidth, compositeHeight);

              viewer.scratchContext.drawImage(video, 0, 0, compositeWidth, compositeHeight);
              viewer.rgbContext.drawImage(
                viewer.scratchCanvas,
                frameWidth,
                0,
                frameWidth,
                compositeHeight,
                0,
                0,
                frameWidth,
                compositeHeight,
              );
              renderDepthFrame(viewer, frameWidth, compositeHeight);
            }
          }

          viewer.animationFrameId = window.requestAnimationFrame(drawFrame);
        };

        viewer.animationFrameId = window.requestAnimationFrame(drawFrame);
      };

      const cleanupPeerConnection = (viewer, nextState = "disconnected") => {
        if (viewer.peerConnection !== null) {
          viewer.peerConnection.onicecandidate = null;
          viewer.peerConnection.ontrack = null;
          viewer.peerConnection.onconnectionstatechange = null;
          viewer.peerConnection.close();
          viewer.peerConnection = null;
        }

        stopFrameRendering(viewer);
        stopVideoStream();

        if (viewer.connectionState === "connecting" || viewer.connectionState === "streaming") {
          viewer.connectionState = nextState;
        }
      };

      const failConnection = (viewer, message) => {
        cleanupPeerConnection(viewer, "failed");
        viewer.connectionState = "failed";
        viewer.errorMessage = message;
        render(viewer);
        publishState(viewer);
      };

      const normalizeAddress = (value) => {
        const trimmed = value.trim();
        if (trimmed === "") {
          return "";
        }
        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
          return trimmed;
        }
        return `http://${trimmed}`;
      };

      class SignalingClient {
        constructor(serverURL) {
          this.serverURL = serverURL;
        }

        async retrieveOffer() {
          let response;
          try {
            response = await fetch(`${this.serverURL}/getOffer`);
          } catch (error) {
            throw new Error(
              "Could not reach the Record3D device. Check that the iPhone and browser are on the same Wi-Fi network."
            );
          }

          if (response.status === 403) {
            throw new Error(
              "Record3D allows only one Wi-Fi receiver at a time. Close the other tab or peer and retry."
            );
          }
          if (!response.ok) {
            throw new Error(`Record3D offer request failed with HTTP ${response.status}.`);
          }
          return response.json();
        }

        async sendAnswer(answer) {
          let response;
          try {
            response = await fetch(`${this.serverURL}/answer`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(answer),
            });
          } catch (error) {
            throw new Error("Could not send the WebRTC answer back to the Record3D device.");
          }

          if (!response.ok) {
            throw new Error(`Record3D answer request failed with HTTP ${response.status}.`);
          }
        }
      }

      const getMetadata = async (serverURL) => {
        let response;
        try {
          response = await fetch(`${serverURL}/metadata`);
        } catch (error) {
          throw new Error("Could not retrieve metadata from the Record3D device.");
        }

        if (!response.ok) {
          throw new Error(`Record3D metadata request failed with HTTP ${response.status}.`);
        }
        return response.json();
      };

      const applyIncomingData = (viewer, nextData) => {
        const persistedAddress = typeof nextData?.device_address === "string" ? nextData.device_address : "";
        const persistedInvDistStd = nextData?.show_inv_dist_std ?? true;
        const persistedEqualization = nextData?.equalize_depth_histogram ?? false;

        if (viewer.connectionState !== "connecting" && viewer.connectionState !== "streaming") {
          viewer.deviceAddress = persistedAddress || viewer.deviceAddress;
        }

        viewer.showInvDistStd = Boolean(persistedInvDistStd);
        viewer.equalizeDepthHistogram = Boolean(persistedEqualization);
        render(viewer);
      };

      const ensureViewer = () => {
        if (root.__record3dWiFiViewer) {
          root.__record3dWiFiViewer.setStateValue = setStateValue;
          applyIncomingData(root.__record3dWiFiViewer, initialData);
          publishState(root.__record3dWiFiViewer);
          return root.__record3dWiFiViewer;
        }

        const viewer = {
          deviceAddress: typeof initialData?.device_address === "string" ? initialData.device_address : "",
          connectionState: "idle",
          errorMessage: "",
          metadata: {},
          peerConnection: null,
          signalingClient: new SignalingClient(""),
          showInvDistStd: initialData?.show_inv_dist_std ?? true,
          equalizeDepthHistogram: initialData?.equalize_depth_histogram ?? false,
          animationFrameId: null,
          rgbContext: ui.rgbCanvas.getContext("2d"),
          depthContext: ui.depthCanvas.getContext("2d", { willReadFrequently: true }),
          scratchCanvas: document.createElement("canvas"),
          scratchContext: null,
          setStateValue,
          cleanup: () => undefined,
        };

        viewer.scratchCanvas = document.createElement("canvas");
        viewer.scratchContext = viewer.scratchCanvas.getContext("2d", { willReadFrequently: true });

        const startReceivingStream = async (submittedAddress) => {
          const normalizedAddress = normalizeAddress(submittedAddress);
          if (normalizedAddress === "") {
            failConnection(viewer, "Enter the Record3D device address shown in the iPhone app.");
            return;
          }

          if (viewer.rgbContext === null || viewer.depthContext === null || viewer.scratchContext === null) {
            failConnection(viewer, "This browser does not support canvas rendering for the Record3D Wi-Fi preview.");
            return;
          }

          cleanupPeerConnection(viewer, "idle");
          viewer.deviceAddress = normalizedAddress;
          viewer.connectionState = "connecting";
          viewer.errorMessage = "";
          viewer.metadata = {};
          viewer.signalingClient.serverURL = normalizedAddress;
          render(viewer);
          publishState(viewer);

          let metadataWarning = "";

          try {
            try {
              viewer.metadata = await getMetadata(normalizedAddress);
            } catch (error) {
              metadataWarning = error.message;
            }

            if (!window.RTCPeerConnection) {
              throw new Error("This browser does not support WebRTC. Use Chrome or Safari for Record3D Wi-Fi.");
            }

            const peerConnection = new RTCPeerConnection();
            let answerSent = false;
            viewer.peerConnection = peerConnection;

            peerConnection.onicecandidate = (event) => {
              if (event.candidate === null && !answerSent && peerConnection.localDescription !== null) {
                answerSent = true;
                viewer.signalingClient
                  .sendAnswer({
                    type: "answer",
                    data: peerConnection.localDescription.sdp,
                  })
                  .catch((error) => failConnection(viewer, error.message));
              }
            };

            peerConnection.ontrack = (event) => {
              ui.sourceVideo.srcObject = event.streams[0];
              void ui.sourceVideo.play().catch(() => undefined);
              startFrameRendering(viewer);
            };

            peerConnection.onconnectionstatechange = () => {
              switch (peerConnection.connectionState) {
                case "connected":
                  viewer.connectionState = "streaming";
                  break;
                case "disconnected":
                  viewer.connectionState = "disconnected";
                  stopFrameRendering(viewer);
                  break;
                case "failed":
                  viewer.connectionState = "failed";
                  viewer.errorMessage = "The Record3D Wi-Fi stream failed. Check the phone app and retry.";
                  stopFrameRendering(viewer);
                  break;
                case "closed":
                  if (viewer.connectionState !== "failed") {
                    viewer.connectionState = "disconnected";
                  }
                  stopFrameRendering(viewer);
                  break;
                default:
                  return;
              }

              if (metadataWarning !== "" && viewer.errorMessage === "") {
                viewer.errorMessage = metadataWarning;
              }

              render(viewer);
              publishState(viewer);
            };

            const remoteOffer = await viewer.signalingClient.retrieveOffer();
            await peerConnection.setRemoteDescription(remoteOffer);
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);

            if (metadataWarning !== "") {
              viewer.errorMessage = metadataWarning;
            }

            render(viewer);
            publishState(viewer);
          } catch (error) {
            failConnection(viewer, error.message || "Failed to connect to the Record3D Wi-Fi stream.");
          }
        };

        ui.form.onsubmit = (event) => {
          event.preventDefault();
          void startReceivingStream(ui.input.value);
        };

        ui.invDistStdToggle.onchange = () => {
          viewer.showInvDistStd = ui.invDistStdToggle.checked;
          render(viewer);
          publishState(viewer);
        };

        ui.depthEqualizationToggle.onchange = () => {
          viewer.equalizeDepthHistogram = ui.depthEqualizationToggle.checked;
          render(viewer);
          publishState(viewer);
        };

        const handleBeforeUnload = () => {
          cleanupPeerConnection(viewer, "disconnected");
        };
        window.addEventListener("beforeunload", handleBeforeUnload);

        viewer.cleanup = () => {
          window.removeEventListener("beforeunload", handleBeforeUnload);
          cleanupPeerConnection(viewer, "disconnected");
        };

        render(viewer);
        publishState(viewer);
        root.__record3dWiFiViewer = viewer;
        return viewer;
      };

      ensureViewer();

      return () => {
        if (!root.isConnected && root.__record3dWiFiViewer) {
          root.__record3dWiFiViewer.cleanup();
          delete root.__record3dWiFiViewer;
        }
      };
    }
    """
).strip()

RECORD3D_WIFI_COMPONENT = st.components.v2.component(
    RECORD3D_WIFI_COMPONENT_NAME,
    html=RECORD3D_WIFI_COMPONENT_HTML,
    css=RECORD3D_WIFI_COMPONENT_CSS,
    js=RECORD3D_WIFI_COMPONENT_JS,
)


def render_record3d_wifi_viewer(
    *,
    initial_state: Record3DWiFiViewerState | None = None,
    key: str = RECORD3D_WIFI_COMPONENT_KEY,
    height: int = RECORD3D_WIFI_COMPONENT_HEIGHT,
) -> Record3DWiFiViewerState:
    """Mount the Record3D Wi-Fi component and return its latest browser state."""
    viewer_state = initial_state or Record3DWiFiViewerState()
    result = RECORD3D_WIFI_COMPONENT(
        key=key,
        height=height,
        data=json.dumps(viewer_state.to_component_data()),
    )
    return Record3DWiFiViewerState.from_component_result(result)


__all__ = [
    "RECORD3D_WIFI_COMPONENT",
    "RECORD3D_WIFI_COMPONENT_CSS",
    "RECORD3D_WIFI_COMPONENT_HEIGHT",
    "RECORD3D_WIFI_COMPONENT_HTML",
    "RECORD3D_WIFI_COMPONENT_JS",
    "RECORD3D_WIFI_COMPONENT_KEY",
    "RECORD3D_WIFI_COMPONENT_NAME",
    "Record3DWiFiConnectionState",
    "Record3DWiFiViewerState",
    "render_record3d_wifi_viewer",
]
