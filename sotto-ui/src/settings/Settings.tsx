import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

type Tab = "general" | "hotkeys" | "models" | "about";

interface SottoConfig {
  mode: string;
  language: string;
  pill_position: string;
  model: string;
  [key: string]: string;
}

const DEFAULT_CONFIG: SottoConfig = {
  mode: "push_to_talk",
  language: "en",
  pill_position: "top-center",
  model: "small.en",
};

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "general", label: "General", icon: "⚙" },
  { id: "hotkeys", label: "Hotkeys", icon: "⌨" },
  { id: "models", label: "Models", icon: "◎" },
  { id: "about", label: "About", icon: "ℹ" },
];

function useConfig() {
  const [config, setConfig] = useState<SottoConfig>(DEFAULT_CONFIG);

  useEffect(() => {
    invoke<Record<string, unknown>>("get_config")
      .then((remote) => {
        const transcription = (remote.transcription as Record<string, string>) || {};
        const feedback = (remote.feedback as Record<string, string>) || {};
        setConfig({
          mode: (remote.mode as string) || DEFAULT_CONFIG.mode,
          language: transcription.language || DEFAULT_CONFIG.language,
          pill_position: feedback.overlay_position || DEFAULT_CONFIG.pill_position,
          model: transcription.model || DEFAULT_CONFIG.model,
        });
      })
      .catch((err) => console.error("Failed to load config:", err));
  }, []);

  const updateValue = (key: string, value: string) => {
    const leafKey = key.split(".").pop() || key;
    const stateKeyMap: Record<string, keyof SottoConfig> = {
      mode: "mode",
      language: "language",
      overlay_position: "pill_position",
      model: "model",
    };
    const stateKey = stateKeyMap[leafKey];
    if (stateKey) {
      setConfig((prev) => ({ ...prev, [stateKey]: value }));
    }
    invoke("set_config_value", { key, value }).catch((err) =>
      console.error(`Failed to set ${key}:`, err),
    );
  };

  return { config, updateValue };
}

export function Settings() {
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const { config, updateValue } = useConfig();

  return (
    <div style={{ display: "flex", height: "100vh", background: "#111111" }}>
      {/* Sidebar */}
      <nav
        style={{
          width: 180,
          borderRight: "1px solid var(--border)",
          padding: "32px 12px 12px",
          display: "flex",
          flexDirection: "column",
          gap: 2,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: "var(--text-primary)",
            padding: "0 12px",
            marginBottom: 20,
            letterSpacing: "-0.01em",
          }}
        >
          Sotto
        </div>

        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "7px 12px",
              borderRadius: 8,
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              fontFamily: "inherit",
              textAlign: "left",
              transition: "all 0.15s ease",
              color: activeTab === tab.id ? "var(--text-primary)" : "var(--text-secondary)",
              background: activeTab === tab.id ? "rgba(255,255,255,0.06)" : "transparent",
            }}
          >
            <span style={{ fontSize: 14, opacity: 0.7, width: 18, textAlign: "center" }}>
              {tab.icon}
            </span>
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ flex: 1, padding: "32px 28px", overflowY: "auto" }}>
        {activeTab === "general" && <GeneralTab config={config} onChange={updateValue} />}
        {activeTab === "hotkeys" && <HotkeyTab />}
        {activeTab === "models" && <ModelTab config={config} onChange={updateValue} />}
        {activeTab === "about" && <AboutTab />}
      </main>
    </div>
  );
}

/* ─── Cards ───────────────────────────────────────────────────── */

function Card({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "16px 20px",
        marginBottom: 12,
      }}
    >
      {title && (
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 14,
          }}
        >
          {title}
        </div>
      )}
      {children}
    </div>
  );
}

function SettingRow({
  label,
  description,
  children,
  isLast = false,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
  isLast?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 0",
        borderBottom: isLast ? "none" : "1px solid var(--border)",
      }}
    >
      <div>
        <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>
          {label}
        </div>
        {description && (
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
            {description}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

function Select({
  options,
  defaultValue,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  defaultValue?: string;
  value?: string;
  onChange?: (value: string) => void;
}) {
  return (
    <select
      value={value}
      defaultValue={value === undefined ? defaultValue : undefined}
      onChange={onChange ? (e) => onChange(e.target.value) : undefined}
      style={{
        appearance: "none",
        background: "var(--bg-input)",
        color: "var(--text-primary)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "6px 28px 6px 10px",
        fontSize: 12,
        fontFamily: "inherit",
        cursor: "pointer",
        outline: "none",
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.4)' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")`,
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 8px center",
      }}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

function Kbd({ children }: { children: string }) {
  return (
    <kbd
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "4px 10px",
        borderRadius: 6,
        fontSize: 12,
        fontFamily: "'Geist Mono', 'SF Mono', monospace",
        background: "var(--bg-input)",
        border: "1px solid var(--border)",
        color: "var(--accent)",
        boxShadow: "0 1px 2px rgba(0,0,0,0.2)",
      }}
    >
      {children}
    </kbd>
  );
}

/* ─── Tabs ────────────────────────────────────────────────────── */

function GeneralTab({
  config,
  onChange,
}: {
  config: SottoConfig;
  onChange: (key: string, value: string) => void;
}) {
  return (
    <>
      <TabHeader title="General" />
      <Card title="Recording">
        <SettingRow label="Mode" description="How Sotto listens for your voice">
          <Select
            options={[
              { value: "push_to_talk", label: "Push to Talk" },
              { value: "always_listening", label: "Always Listening" },
            ]}
            value={config.mode}
            onChange={(v) => onChange("mode", v)}
          />
        </SettingRow>
        <SettingRow label="Language" description="Transcription language" isLast>
          <Select
            options={[
              { value: "en", label: "English" },
              { value: "auto", label: "Auto-detect" },
            ]}
            value={config.language}
            onChange={(v) => onChange("transcription.language", v)}
          />
        </SettingRow>
      </Card>
      <Card title="Appearance">
        <SettingRow label="Pill Position" description="Recording indicator location" isLast>
          <Select
            options={[
              { value: "top-center", label: "Top Center" },
              { value: "top-left", label: "Top Left" },
              { value: "top-right", label: "Top Right" },
              { value: "bottom-center", label: "Bottom Center" },
            ]}
            value={config.pill_position}
            onChange={(v) => onChange("feedback.overlay_position", v)}
          />
        </SettingRow>
      </Card>
    </>
  );
}

function HotkeyTab() {
  return (
    <>
      <TabHeader title="Hotkeys" />
      <Card title="Keyboard Shortcuts">
        <SettingRow label="Toggle Recording" description="Start/stop recording">
          <Kbd>⌘ ⇧ S</Kbd>
        </SettingRow>
        <SettingRow label="Open Settings" description="Open this window" isLast>
          <Kbd>⌘ ,</Kbd>
        </SettingRow>
      </Card>
      <Card>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
          Shortcuts are managed by the system and cannot be customized yet.
        </div>
      </Card>
    </>
  );
}

function ModelTab({
  config,
  onChange,
}: {
  config: SottoConfig;
  onChange: (key: string, value: string) => void;
}) {
  return (
    <>
      <TabHeader title="Whisper Model" />
      <Card title="Model Selection">
        <SettingRow
          label="Active Model"
          description="Larger models are more accurate but use more memory"
          isLast
        >
          <Select
            options={[
              { value: "tiny.en", label: "Tiny (39M)" },
              { value: "base.en", label: "Base (74M)" },
              { value: "small.en", label: "Small (244M)" },
              { value: "medium.en", label: "Medium (769M)" },
              { value: "large-v3", label: "Large v3 (1.5B)" },
            ]}
            value={config.model}
            onChange={(v) => onChange("transcription.model", v)}
          />
        </SettingRow>
      </Card>
      <Card>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
          All models run locally via faster-whisper with Metal GPU acceleration.
          No data leaves your Mac.
        </div>
      </Card>
    </>
  );
}

function AboutTab() {
  return (
    <>
      <TabHeader title="About" />
      <Card>
        <div style={{ textAlign: "center", padding: "20px 0" }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "var(--accent-dim)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 12,
            }}
          >
            <span style={{ fontSize: 24 }}>◉</span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Sotto</div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            Version 0.1.0
          </div>
        </div>
      </Card>
      <Card>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.7 }}>
          Local voice control powered by Whisper AI.<br />
          All processing happens on your Mac. No cloud. No telemetry.
        </div>
      </Card>
    </>
  );
}

function TabHeader({ title }: { title: string }) {
  return (
    <h2
      style={{
        fontSize: 16,
        fontWeight: 600,
        color: "var(--text-primary)",
        marginBottom: 16,
        letterSpacing: "-0.01em",
      }}
    >
      {title}
    </h2>
  );
}
