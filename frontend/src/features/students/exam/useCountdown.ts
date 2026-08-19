import { useEffect, useState } from "react";

/** Ticking seconds-remaining countdown to a fixed deadline. Returns null
 * once expired (caller decides what "expired" means, e.g. auto-submit). */
export function useCountdown(deadline: Date | null): number | null {
  const [secondsLeft, setSecondsLeft] = useState<number | null>(() =>
    deadline ? Math.max(0, Math.floor((deadline.getTime() - Date.now()) / 1000)) : null,
  );

  useEffect(() => {
    if (!deadline) {
      setSecondsLeft(null);
      return;
    }
    const tick = () => setSecondsLeft(Math.max(0, Math.floor((deadline.getTime() - Date.now()) / 1000)));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [deadline]);

  return secondsLeft;
}

export function formatCountdown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}
