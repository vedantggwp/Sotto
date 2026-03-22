import { listen, emit } from "@tauri-apps/api/event";
import type { RecordingState, SidecarMessage } from "./types";

type StateCallback = (state: RecordingState) => void;
type LevelCallback = (level: number) => void;
type TextCallback = (text: string) => void;
type ErrorCallback = (error: string) => void;

interface EngineCallbacks {
  onStateChange?: StateCallback;
  onAudioLevel?: LevelCallback;
  onTranscription?: TextCallback;
  onError?: ErrorCallback;
}

export function connectToEngine(callbacks: EngineCallbacks) {
  const unlisteners: (() => void)[] = [];

  const setup = async () => {
    const unlisten = await listen<SidecarMessage>("sotto://engine", (event) => {
      const msg = event.payload;
      switch (msg.type) {
        case "state_change":
          if (msg.state) callbacks.onStateChange?.(msg.state);
          break;
        case "audio_level":
          if (msg.level !== undefined) callbacks.onAudioLevel?.(msg.level);
          break;
        case "transcription":
          if (msg.text) callbacks.onTranscription?.(msg.text);
          break;
        case "error":
          if (msg.error) callbacks.onError?.(msg.error);
          break;
      }
    });
    unlisteners.push(unlisten);
  };

  setup().catch((err) => {
    console.error("[sotto] engine connection failed:", err);
    callbacks.onError?.(String(err));
  });

  return () => {
    unlisteners.forEach((fn) => fn());
  };
}

export async function sendToEngine(command: string, data?: Record<string, unknown>) {
  await emit("sotto://command", { command, ...data });
}
