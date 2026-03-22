import { useEffect, useRef, useCallback, useState } from "react";
import { AudioDots } from "./AudioDots";
import { connectToEngine } from "../lib/engine";
import type { RecordingState } from "../lib/types";

export function Pill() {
  const [state, setState] = useState<RecordingState>("idle");
  const [audioLevel, setAudioLevel] = useState(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleStateChange = useCallback((newState: RecordingState) => {
    setState(newState);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (newState === "done") {
      timeoutRef.current = setTimeout(() => setState("idle"), 1800);
    }
  }, []);

  const handleError = useCallback(() => {
    setState("error");
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setState("idle"), 3000);
  }, []);

  useEffect(() => {
    const disconnect = connectToEngine({
      onStateChange: handleStateChange,
      onAudioLevel: setAudioLevel,
      onError: handleError,
    });
    return () => {
      disconnect();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [handleStateChange, handleError]);

  const isError = state === "error";
  const isVisible = state !== "idle";
  const isListening = state === "listening";
  const isDone = state === "done";
  const isProcessing = state === "transcribing" || state === "formatting";

  const pillClass = [
    "pill",
    isVisible && "visible",
    isListening && "listening",
    isError && "error",
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

      {isError && (
        <svg
          className="error-icon"
          viewBox="0 0 24 24"
          width="14"
          height="14"
          fill="none"
          stroke="#ef4444"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      )}
    </div>
  );
}
