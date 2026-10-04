import type { ProcessResult } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const CARTOON_TIMEOUT_MS = 120_000;

export type SavePhotoResult = { ok: true; photo: string } | { ok: false; error: string };

/** Save a webcam capture to camera/ on the backend. */
export async function savePortraitPhoto(file: File): Promise<SavePhotoResult> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/portrait/photo`, { method: "POST", body: formData });
  } catch {
    return { ok: false, error: "Could not reach the backend. Is it running on port 8000?" };
  }

  if (!response.ok) {
    return { ok: false, error: await readErrorMessage(response, "Saving the photo failed") };
  }

  const body = (await response.json()) as { photo: string };
  return { ok: true, photo: body.photo };
}

/** Let Vin turn a saved photo into a cartoon SVG (also saved to image/). */
export async function cartoonizePortrait(photo: string): Promise<ProcessResult> {
  const formData = new FormData();
  formData.append("photo", photo);

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), CARTOON_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/portrait/cartoon`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return { ok: false, error: "Vin took too long. Please try again." };
    }
    return { ok: false, error: "Could not reach the backend. Is it running on port 8000?" };
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    return { ok: false, error: await readErrorMessage(response, "Vin could not sketch this photo") };
  }

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? photo.replace(/\.[^.]+$/, ".svg");
  return { ok: true, blob: await response.blob(), filename };
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Response was not JSON.
  }
  return `${fallback} (${response.status}).`;
}
