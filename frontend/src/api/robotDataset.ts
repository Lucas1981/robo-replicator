import type { ProcessResult } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const ROBOT_TIMEOUT_MS = 120_000;

export async function createRobotDataset(
  svgBlob: Blob,
  svgFilename: string,
): Promise<ProcessResult> {
  const formData = new FormData();
  formData.append("file", svgBlob, svgFilename);

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), ROBOT_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/robot-dataset`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return {
        ok: false,
        error: "Robot dataset generation timed out. Try again or use the offline script.",
      };
    }
    return {
      ok: false,
      error: "Could not reach the backend. Is it running on port 8000?",
    };
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    const message = await readErrorMessage(response);
    return { ok: false, error: message };
  }

  const blob = await response.blob();
  const filename = filenameFromResponse(response, svgFilename);
  return { ok: true, blob, filename };
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | { msg: string }[] };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // Response was not JSON.
  }
  return `Robot dataset generation failed (${response.status}).`;
}

function filenameFromResponse(response: Response, sourceName: string): string {
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  if (match?.[1]) return match[1];

  const baseName = sourceName.replace(/\.[^.]+$/, "").replace(/-paths$/, "") || "output";
  return `${baseName}-draw.zip`;
}
