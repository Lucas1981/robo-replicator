import { useEffect, useRef, useState } from "react";

type CapturePhase = "preview" | "flash" | "processing";

type CameraCaptureModalProps = {
  open: boolean;
  onClose: () => void;
  onCapture: (file: File) => void;
};

export default function CameraCaptureModal({ open, onClose, onCapture }: CameraCaptureModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [phase, setPhase] = useState<CapturePhase>("preview");
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!open) {
      stopStream();
      setPhase("preview");
      setError(null);
      setStarting(false);
      return;
    }

    let cancelled = false;
    setStarting(true);
    setError(null);

    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          void video.play();
        }
        setStarting(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setStarting(false);
        if (err instanceof DOMException && err.name === "NotAllowedError") {
          setError("Camera access was denied. Allow camera permission and try again.");
        } else if (err instanceof DOMException && err.name === "NotFoundError") {
          setError("No camera was found on this device.");
        } else {
          setError("Could not access the camera.");
        }
      });

    return () => {
      cancelled = true;
      stopStream();
    };
  }, [open]);

  function stopStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    const video = videoRef.current;
    if (video) video.srcObject = null;
  }

  async function handleTakePicture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || phase !== "preview") return;

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (width === 0 || height === 0) return;

    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return;

    context.drawImage(video, 0, 0, width, height);

    setPhase("flash");
    await wait(180);
    setPhase("processing");
    stopStream();

    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", 0.92);
    });

    if (!blob) {
      setError("Could not save the photo. Try again.");
      setPhase("preview");
      return;
    }

    await wait(500);

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const file = new File([blob], `webcam-capture-${timestamp}.jpg`, { type: "image/jpeg" });
    onCapture(file);
    onClose();
  }

  if (!open) return null;

  return (
    <div className="camera-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="camera-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="camera-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="camera-modal-title" className="camera-modal-title">
          Take a photo
        </h2>

        <div className="camera-preview-wrap">
          <video
            ref={videoRef}
            className={`camera-preview${phase !== "preview" ? " camera-preview-hidden" : ""}`}
            autoPlay
            playsInline
            muted
          />
          <canvas ref={canvasRef} hidden />

          {starting && <p className="camera-overlay-message">Starting camera…</p>}

          {error && <p className="camera-overlay-message camera-overlay-error">{error}</p>}

          {phase === "flash" && <div className="camera-flash" aria-hidden="true" />}

          {phase === "processing" && (
            <p className="camera-overlay-message">Picture taken. Preparing image…</p>
          )}
        </div>

        <div className="camera-modal-actions">
          <button
            type="button"
            disabled={starting || !!error || phase !== "preview"}
            onClick={() => void handleTakePicture()}
          >
            Take picture
          </button>
          <button type="button" className="secondary" disabled={phase === "processing"} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
