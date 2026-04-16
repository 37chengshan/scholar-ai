import { create } from "zustand";
import { persist } from "zustand/middleware";

type FontSize = "small" | "medium" | "large" | "extra-large";

const fontSizeMap: Record<FontSize, string> = {
  small: "14px",
  medium: "16px",
  large: "18px",
  "extra-large": "20px",
};

/** Apply the font-size CSS variable to the document root (no-op in non-browser environments). */
function applyFontSize(size: FontSize): void {
  if (typeof document !== "undefined") {
    document.documentElement.style.setProperty(
      "--base-font-size",
      fontSizeMap[size],
    );
  }
}

interface SettingsState {
  fontSize: FontSize;
  setFontSize: (size: FontSize) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      fontSize: "medium",
      setFontSize: (size) => {
        set({ fontSize: size });
        applyFontSize(size);
      },
    }),
    { name: "scholarai-settings" },
  ),
);

// Initialize the CSS variable from the persisted value on module load.
// The guard inside applyFontSize prevents crashes in Vitest / SSR environments
// where `document` does not exist.
applyFontSize(useSettingsStore.getState().fontSize);
