import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type ReadRightTab = 'notes' | 'annotations' | 'summary';

interface ReadPreferencesState {
  rightTab: ReadRightTab;
  isPanelOpen: boolean;
  isFullscreen: boolean;
  panelWidth: number;
  setRightTab: (tab: ReadRightTab) => void;
  setIsPanelOpen: (isOpen: boolean) => void;
  setIsFullscreen: (isFullscreen: boolean) => void;
  setPanelWidth: (width: number) => void;
}

export const useReadPreferencesStore = create<ReadPreferencesState>()(
  persist(
    (set) => ({
      rightTab: 'notes',
      isPanelOpen: true,
      isFullscreen: false,
      panelWidth: 360,
      setRightTab: (rightTab) => set({ rightTab }),
      setIsPanelOpen: (isPanelOpen) => set({ isPanelOpen }),
      setIsFullscreen: (isFullscreen) => set({ isFullscreen }),
      setPanelWidth: (panelWidth) => set({ panelWidth }),
    }),
    {
      name: 'scholar-ai-read-preferences',
      storage: createJSONStorage(() => localStorage),
      partialize: ({ rightTab, isPanelOpen, panelWidth }) => ({
        rightTab,
        isPanelOpen,
        panelWidth,
      }),
    },
  ),
);