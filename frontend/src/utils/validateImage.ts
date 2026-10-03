import type { ImageValidationResult } from "../types";

const ACCEPTED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
]);

const MAX_BYTES = 10 * 1024 * 1024;
const MIN_DIMENSION = 64;
const MAX_DIMENSION = 8192;

function loadImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();

    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not decode image"));
    };

    img.src = url;
  });
}

export async function validateImage(file: File): Promise<ImageValidationResult> {
  if (!ACCEPTED_TYPES.has(file.type)) {
    return {
      ok: false,
      reason: "Use a JPEG, PNG, WebP, or GIF image.",
    };
  }

  if (file.size === 0) {
    return { ok: false, reason: "The file is empty." };
  }

  if (file.size > MAX_BYTES) {
    return { ok: false, reason: "Image must be 10 MB or smaller." };
  }

  try {
    const { width, height } = await loadImageDimensions(file);

    if (width < MIN_DIMENSION || height < MIN_DIMENSION) {
      return {
        ok: false,
        reason: `Image must be at least ${MIN_DIMENSION}×${MIN_DIMENSION} pixels.`,
      };
    }

    if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
      return {
        ok: false,
        reason: `Image must be at most ${MAX_DIMENSION}×${MAX_DIMENSION} pixels.`,
      };
    }

    return { ok: true, width, height };
  } catch {
    return { ok: false, reason: "The file does not appear to be a valid image." };
  }
}
