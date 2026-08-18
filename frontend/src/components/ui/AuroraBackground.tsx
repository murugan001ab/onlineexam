export function AuroraBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-40 -top-40 size-[520px] rounded-full bg-brand-600/30 animate-blob animate-glow" />
      <div className="absolute -right-32 top-1/3 size-[420px] rounded-full bg-accent-500/20 animate-blob animate-glow [animation-delay:2s]" />
      <div className="absolute bottom-[-200px] left-1/3 size-[460px] rounded-full bg-brand-500/20 animate-blob animate-glow [animation-delay:4s]" />
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
    </div>
  );
}
