import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type FontSize = 'small' | 'medium' | 'large' | 'extra-large';

const fontSizeMap: Record<FontSize, string> = {
  'small': '14px',
  'medium': '16px',
  'large': '18px',
  'extra-large': '20px',
};

interface SettingsState {
  fontSize: FontSize;
  setFontSize: (size: FontSize) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      fontSize: 'medium',
      setFontSize: (size) => {
        set({ fontSize: size });
        document.documentElement.style.setProperty('--base-font-size', fontSizeMap[size]);
      },
    }),
    { name: 'scholarai-settings' }
  )
);

// Initialize CSS variable on load
const initialSize = useSettingsStore.getState().fontSize;
document.documentElement.style.setProperty('--base-font-size', fontSizeMap[initialSize]);
