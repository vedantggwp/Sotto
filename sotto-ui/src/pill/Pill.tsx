import { useEffect, useRef, useCallback, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { AudioDots } from "./AudioDots";
import { connectToEngine } from "../lib/engine";
import type { RecordingState } from "../lib/types";

export function Pill() {
  const [state, setState] = useState<RecordingState>("listening");
  const [audioLevel, setAudioLevel] = useState(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleStateChange = useCallback((newState: RecordingState) => {
    setState(newState);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (newState === "done") {
      timeoutRef.current = setTimeout(() => setState("idle"), 1800);
    }
  }, []);

  useEffect(() => {
    const disconnect = connectToEngine({
      onStateChange: handleStateChange,
      onAudioLevel: setAudioLevel,
    });
    return () => {
      disconnect();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [handleStateChange]);

  // Demo: simulate natural speech-like audio levels
  useEffect(() => {
    if (state !== "listening") return;
    let frame: number;
    const simulate = () => {
      const t = performance.now() / 1000;
      // Layered sine waves for organic speech-like envelope
      const base = 0.25;
      const speech = 0.3 * Math.sin(t * 1.8) * Math.sin(t * 0.7);
      const breath = 0.12 * Math.sin(t * 4.7);
      const detail = 0.08 * Math.sin(t * 11.3);
      const noise = 0.05 * (Math.random() - 0.5);
      setAudioLevel(Math.max(0, Math.min(1, base + speech + breath + detail + noise)));
      frame = requestAnimationFrame(simulate);
    };
    frame = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(frame);
  }, [state]);

  // Cycle states via click OR global shortcut (Cmd+Shift+D)
  useEffect(() => {
    const cycle: RecordingState[] = ["listening", "transcribing", "done", "idle", "listening"];
    let idx = 0;
    const advance = () => {
      idx = (idx + 1) % cycle.length;
      handleStateChange(cycle[idx]);
    };
    window.addEventListener("click", advance);
    let unlisten: (() => void) | undefined;
    listen("sotto://demo-cycle", advance).then((fn) => { unlisten = fn; });
    return () => {
      window.removeEventListener("click", advance);
      unlisten?.();
    };
  }, [handleStateChange]);

  const isVisible = state !== "idle";
  const isListening = state === "listening";
  const isDone = state === "done";
  const isProcessing = state === "transcribing" || state === "formatting";

  const pillClass = [
    "pill",
    isVisible && "visible",
    isListening && "listening",
  ].filter(Boolean).join(" ");

  return (
    <div className={pillClass}>
      {isListening && <AudioDots level={audioLevel} />}

      {isProcessing && (
        <>
          <div className="waveform">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="bar idle" />
            ))}
          </div>
          <div className="status-dot transcribing" />
        </>
      )}

      {isDone && (
        <svg
          className={`checkmark ${isDone ? "visible" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      )}
    </div>
  );
}
