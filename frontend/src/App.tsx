import { useEffect, useRef, useState } from "react";
import { processImage } from "./api/processImage";
import type { AppStatus } from "./types";
import { validateImage } from "./utils/validateImage";
import "./App.css";

export default function App() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageInfo, setImageInfo] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [output, setOutput] = useState<{ blob: Blob; filename: string } | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function handleFile(selected: File | null) {
    setOutput(null);

    if (!selected) {
      setFile(null);
      setPreviewUrl(null);
      setImageInfo(null);
      setStatus("idle");
      setMessage(null);
      return;
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
      return;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(selected));
    setImageInfo(`${validation.width}×${validation.height} · ${formatBytes(selected.size)}`);
    setStatus("ready");
    setMessage("Image looks good. Ready to process.");
  }

  async function handleProcess() {
    if (!file || status !== "ready") return;

    setStatus("processing");
    setMessage("Processing image…");
    setOutput(null);

    const result = await processImage(file);

    if (!result.ok) {
      setStatus("error");
      setMessage(result.error);
      return;
    }

    setOutput({ blob: result.blob, filename: result.filename });
    setStatus("success");
    setMessage("Processing complete. You can download the output.");
  }

  function handleDownload() {
    if (!output) return;

    const url = URL.createObjectURL(output.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = output.filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  const canProcess = status === "ready" && file !== null;
  const canDownload = status === "success" && output !== null;

  return (
    <main className="app">
      <header className="header">
        <h1>Robo Replicator</h1>
        <p>Upload an image to generate a robot-ready outline drawing.</p>
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

        <button type="button" className="secondary" onClick={() => inputRef.current?.click()}>
          Choose file
        </button>

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
          {status === "processing" ? "Processing…" : "Process file"}
        </button>

        <button type="button" className="secondary" disabled={!canDownload} onClick={handleDownload}>
          Download
        </button>
      </div>
    </main>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
