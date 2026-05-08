import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

interface NotesPreferencesState {
  selectedFolderId: string | null;
  tagFilter: string;
  setSelectedFolderId: (selectedFolderId: string | null) => void;
  setTagFilter: (tagFilter: string) => void;
}

export const useNotesPreferencesStore = create<NotesPreferencesState>()(
  persist(
    (set) => ({
      selectedFolderId: null,
      tagFilter: 'all',
      setSelectedFolderId: (selectedFolderId) =>
        set((state) =>
          state.selectedFolderId === selectedFolderId ? state : { selectedFolderId }
        ),
      setTagFilter: (tagFilter) =>
        set((state) => (state.tagFilter === tagFilter ? state : { tagFilter })),
    }),
    {
      name: 'scholar-ai-notes-preferences',
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
