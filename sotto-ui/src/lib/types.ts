export type RecordingState = "idle" | "listening" | "transcribing" | "formatting" | "done" | "error";

export type PillPosition =
  | "top-left"
  | "top-center"
  | "top-right"
  | "bottom-left"
  | "bottom-center"
  | "bottom-right";

export interface SottoConfig {
  mode: "push-to-talk" | "always-listening";
  model: string;
  hotkey: string;
  pillPosition: PillPosition;
  language: string;
}

export interface SidecarMessage {
  type: "state_change" | "audio_level" | "transcription" | "error";
  state?: RecordingState;
  level?: number;
  text?: string;
  error?: string;
}
