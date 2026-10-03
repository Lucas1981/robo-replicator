export type ImageValidationResult =
  | { ok: true; width: number; height: number }
  | { ok: false; reason: string };

export type ProcessResult =
  | { ok: true; blob: Blob; filename: string }
  | { ok: false; error: string };

export type AppStatus = "idle" | "validating" | "ready" | "processing" | "success" | "error";
