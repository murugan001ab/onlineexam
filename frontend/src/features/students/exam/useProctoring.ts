import { useCallback, useEffect, useRef, useState } from "react";
import { proctoringApi } from "@/api/proctoring";
import type { ProctoringEventIn, ProctoringEventType } from "@/types/proctoring";

const FLUSH_INTERVAL_MS = 5_000;
const SNAPSHOT_INTERVAL_MS = 45_000;

interface UseProctoringOptions {
  attemptId: number | null;
  active: boolean;
  cameraRequired: boolean;
  onDisqualified: () => void;
}

interface UseProctoringResult {
  isFullscreen: boolean;
  warningCount: number;
  maxWarnings: number;
  cameraError: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  enterFullscreen: () => Promise<void>;
  logEvent: (type: ProctoringEventType, metadata?: unknown) => void;
}

/** Wires up every anti-cheat signal for the exam-taking page: fullscreen
 * enforcement, tab-switch/window-blur detection, copy/paste/right-click/
 * devtools blocking, and (if the exam requires it) a periodic webcam
 * snapshot. Events are buffered and flushed in small batches so a flaky
 * connection doesn't drop signal or spam the network. */
export function useProctoring({ attemptId, active, cameraRequired, onDisqualified }: UseProctoringOptions): UseProctoringResult {
  const [isFullscreen, setIsFullscreen] = useState(() => Boolean(document.fullscreenElement));
  const [warningCount, setWarningCount] = useState(0);
  const [maxWarnings, setMaxWarnings] = useState(3);
  const [cameraError, setCameraError] = useState<string | null>(null);

  const bufferRef = useRef<ProctoringEventIn[]>([]);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const disqualifiedRef = useRef(false);

  const logEvent = useCallback((event_type: ProctoringEventType, metadata?: unknown) => {
    bufferRef.current.push({ event_type, metadata, occurred_at: new Date().toISOString() });
  }, []);

  const enterFullscreen = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen();
    } catch {
      // Some browsers only allow this from a direct user gesture; the caller
      // re-shows the "Return to fullscreen" prompt if it still fails.
    }
  }, []);

  // ---- flush buffered events on an interval ----
  useEffect(() => {
    if (!active || !attemptId) return;
    const interval = setInterval(async () => {
      if (disqualifiedRef.current || bufferRef.current.length === 0) return;
      const batch = bufferRef.current;
      bufferRef.current = [];
      try {
        const result = await proctoringApi.sendEvents(attemptId, batch);
        setWarningCount(result.warning_count);
        setMaxWarnings(result.max_warnings);
        if (result.disqualified && !disqualifiedRef.current) {
          disqualifiedRef.current = true;
          onDisqualified();
        }
      } catch {
        // Put the batch back so the next tick retries it.
        bufferRef.current = [...batch, ...bufferRef.current];
      }
    }, FLUSH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [active, attemptId, onDisqualified]);

  // ---- tab switch / window blur / fullscreen exit detection ----
  useEffect(() => {
    if (!active) return;

    function onVisibilityChange() {
      if (document.hidden) logEvent("tab_switch");
    }
    function onBlur() {
      logEvent("window_blur");
    }
    function onFullscreenChange() {
      const fs = Boolean(document.fullscreenElement);
      setIsFullscreen(fs);
      if (!fs) logEvent("fullscreen_exit");
    }
    function onContextMenu(e: MouseEvent) {
      e.preventDefault();
      logEvent("right_click");
    }
    function onCopy() {
      logEvent("copy");
    }
    function onPaste() {
      logEvent("paste");
    }
    function onKeyDown(e: KeyboardEvent) {
      const key = e.key.toLowerCase();
      const isDevtoolsCombo =
        key === "f12" ||
        (e.ctrlKey && e.shiftKey && ["i", "j", "c"].includes(key)) ||
        (e.ctrlKey && key === "u");
      if (isDevtoolsCombo) {
        e.preventDefault();
        logEvent("devtools");
      }
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("blur", onBlur);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("contextmenu", onContextMenu);
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      document.removeEventListener("contextmenu", onContextMenu);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [active, logEvent]);

  // ---- camera stream + periodic snapshot ----
  useEffect(() => {
    if (!active || !cameraRequired) return;
    let cancelled = false;

    navigator.mediaDevices
      ?.getUserMedia({ video: { width: 320, height: 240 }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => {
        if (!cancelled) setCameraError("Camera access is required for this exam but could not be started.");
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [active, cameraRequired]);

  useEffect(() => {
    if (!active || !cameraRequired || !attemptId) return;
    const interval = setInterval(() => {
      const video = videoRef.current;
      const stream = streamRef.current;
      if (!video || !stream || video.readyState < 2) {
        logEvent("face_missing");
        return;
      }
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 320;
      canvas.height = video.videoHeight || 240;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.6);
      proctoringApi.sendSnapshot(attemptId, dataUrl).catch(() => {
        /* best-effort — a missed snapshot isn't worth surfacing to the student */
      });
    }, SNAPSHOT_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [active, attemptId, cameraRequired, logEvent]);

  return { isFullscreen, warningCount, maxWarnings, cameraError, videoRef, enterFullscreen, logEvent };
}
