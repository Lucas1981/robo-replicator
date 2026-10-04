import { useEffect, useRef, useState } from "react";
import { cartoonizePortrait, savePortraitPhoto } from "./api/portrait";
import { processImage } from "./api/processImage";
import { createRobotDataset } from "./api/robotDataset";
import CameraCaptureModal from "./components/CameraCaptureModal";
import type { AppStatus } from "./types";
import { validateImage } from "./utils/validateImage";
import "./App.css";

type DownloadOutput = { blob: Blob; filename: string };

export default function App() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageInfo, setImageInfo] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [svgOutput, setSvgOutput] = useState<DownloadOutput | null>(null);
  const [robotOutput, setRobotOutput] = useState<DownloadOutput | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  // Set when the image came from the camera and was saved to camera/; Vin then sketches it.
  const [savedPhoto, setSavedPhoto] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function handleFile(selected: File | null): Promise<boolean> {
    setSvgOutput(null);
    setRobotOutput(null);
    setSavedPhoto(null);

    if (!selected) {
      setFile(null);
      setPreviewUrl(null);
      setImageInfo(null);
      setStatus("idle");
      setMessage(null);
      return false;
    }

    setFile(selected);
    setStatus("validating");
    setMessage("Checking image…");

    const validation = await validateImage(selected);

    if (!validation.ok) {
      setPreviewUrl(null);
      setImageInfo(null);
      setStatus("error");
      setMessage(validation.reason);
      return false;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(selected));
    setImageInfo(`${validation.width}×${validation.height} · ${formatBytes(selected.size)}`);
    setStatus("ready");
    setMessage("Image looks good. Ready to process.");
    return true;
  }

  async function handleCapture(captured: File) {
    if (!(await handleFile(captured))) return;

    setStatus("validating");
    setMessage("Saving photo…");
    const result = await savePortraitPhoto(captured);

    if (!result.ok) {
      setStatus("error");
      setMessage(result.error);
      return;
    }

    setSavedPhoto(result.photo);
    setStatus("ready");
    setMessage(`Photo saved to camera/${result.photo}. Click "Sketch with Vin" to make the cartoon.`);
  }

  async function handleProcess() {
    if (!file || status !== "ready") return;

    setStatus("processing");
    setMessage(
      savedPhoto
        ? "Vin is sketching your portrait… this usually takes 10–30 seconds."
        : "Generating outline and converting to paths… this can take 30–90 seconds.",
    );
    setSvgOutput(null);
    setRobotOutput(null);

    const result = savedPhoto ? await cartoonizePortrait(savedPhoto) : await processImage(file);

    if (!result.ok) {
      setStatus("error");
      setMessage(result.error);
      return;
    }

    setSvgOutput({ blob: result.blob, filename: result.filename });
    setStatus("success");
    setMessage(
      savedPhoto
        ? `Vin's cartoon saved to image/${result.filename}. Download the SVG or generate a robot replay dataset.`
        : "SVG paths ready. Download the SVG or generate a robot replay dataset.",
    );
  }

  async function handleGenerateRobotDataset() {
    if (!svgOutput) return;

    setStatus("generating_robot");
    setMessage("Converting SVG paths to a LeRobot replay dataset…");
    setRobotOutput(null);

    const result = await createRobotDataset(svgOutput.blob, svgOutput.filename);

    if (!result.ok) {
      setStatus("success");
      setMessage(result.error);
      return;
    }

    setRobotOutput({ blob: result.blob, filename: result.filename });
    setStatus("robot_ready");
    setMessage("Robot dataset ready. Unzip and replay with lerobot-replay.");
  }

  function handleDownload(output: DownloadOutput | null) {
    if (!output) return;

    const url = URL.createObjectURL(output.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = output.filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  const canProcess = status === "ready" && file !== null;
  const canDownloadSvg =
    (status === "success" || status === "generating_robot" || status === "robot_ready") &&
    svgOutput !== null;
  const canGenerateRobot =
    (status === "success" || status === "robot_ready") && svgOutput !== null;
  const canDownloadRobot = status === "robot_ready" && robotOutput !== null;

  return (
    <main className="app">
      <header className="header">
        <h1>Robotticelli</h1>
        <p>Upload or capture an image to generate SVG paths, then convert them for SO-101 replay.</p>
      </header>

      <section
        className="dropzone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const dropped = event.dataTransfer.files[0] ?? null;
          void handleFile(dropped);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          hidden
          onChange={(event) => void handleFile(event.target.files?.[0] ?? null)}
        />

        {previewUrl ? (
          <img src={previewUrl} alt="Uploaded preview" className="preview" />
        ) : (
          <div className="dropzone-placeholder">
            <p>Drag and drop an image here</p>
            <p className="muted">or</p>
          </div>
        )}

        <div className="dropzone-actions">
          <button type="button" className="secondary" onClick={() => inputRef.current?.click()}>
            Choose file
          </button>
          <button type="button" className="secondary" onClick={() => setCameraOpen(true)}>
            Take photo
          </button>
        </div>

        {file && <p className="file-name">{file.name}</p>}
        {imageInfo && <p className="file-meta">{imageInfo}</p>}
      </section>

      {message && (
        <p className={`status status-${status}`} role="status">
          {message}
        </p>
      )}

      <div className="actions">
        <button type="button" disabled={!canProcess} onClick={() => void handleProcess()}>
          {status === "processing" ? "Processing…" : savedPhoto ? "Sketch with Vin" : "Process file"}
        </button>

        <button
          type="button"
          className="secondary"
          disabled={!canDownloadSvg}
          onClick={() => handleDownload(svgOutput)}
        >
          Download SVG
        </button>

        <button
          type="button"
          className="secondary"
          disabled={!canGenerateRobot}
          onClick={() => void handleGenerateRobotDataset()}
        >
          {status === "generating_robot" ? "Generating…" : "Generate robot dataset"}
        </button>

        <button
          type="button"
          className="secondary"
          disabled={!canDownloadRobot}
          onClick={() => handleDownload(robotOutput)}
        >
          Download robot zip
        </button>
      </div>

      <CameraCaptureModal
        open={cameraOpen}
        onClose={() => setCameraOpen(false)}
        onCapture={(captured) => void handleCapture(captured)}
      />
    </main>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
