import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type UploadQueueStatus =
  | 'pending'
  | 'preparing'
  | 'uploading'
  | 'queued'
  | 'completed'
  | 'cancelled'
  | 'failed'
  | 'needs_file_reselect';

export interface UploadQueueItem {
  id: string;
  file?: File;
  fileName: string;
  sizeBytes: number;
  mimeType: string;
  lastModified: number;
  progress: number;
  status: UploadQueueStatus;
  error?: string;
  importJobId?: string;
  uploadSessionId?: string;
}

interface PersistedUploadQueueItem extends Omit<UploadQueueItem, 'file'> {}

interface UploadWorkspaceState {
  items: UploadQueueItem[];
  addFiles: (files: File[]) => void;
  updateItem: (id: string, updater: (item: UploadQueueItem) => UploadQueueItem) => void;
  removeItem: (id: string) => void;
  clear: () => void;
}

function createUploadId(): string {
  return Math.random().toString(36).slice(2, 11);
}

function normalizePersistedItem(item: PersistedUploadQueueItem): UploadQueueItem {
  if (item.status === 'queued' || item.status === 'completed' || item.status === 'cancelled') {
    return item;
  }

  return {
    ...item,
    status: 'needs_file_reselect',
    error: item.error ?? '请重新选择原始文件后继续上传',
  };
}

export const useUploadWorkspaceStore = create<UploadWorkspaceState>()(
  persist(
    (set) => ({
      items: [],
      addFiles: (files) =>
        set((state) => {
          const nextItems = [...state.items];

          for (const file of files) {
            const existingIndex = nextItems.findIndex(
              (item) =>
                item.file === undefined &&
                (item.status === 'needs_file_reselect' || item.status === 'cancelled') &&
                item.fileName === file.name &&
                item.sizeBytes === file.size &&
                item.lastModified === file.lastModified
            );

            if (existingIndex >= 0) {
              const existing = nextItems[existingIndex];
              nextItems[existingIndex] = {
                ...existing,
                file,
                mimeType: file.type || existing.mimeType || 'application/pdf',
                lastModified: file.lastModified,
                status: 'pending',
                error: undefined,
                importJobId: undefined,
                uploadSessionId: undefined,
                progress: 0,
              };
              continue;
            }

            nextItems.push({
              id: createUploadId(),
              file,
              fileName: file.name,
              sizeBytes: file.size,
              mimeType: file.type || 'application/pdf',
              lastModified: file.lastModified,
              progress: 0,
              status: 'pending',
            });
          }

          return { items: nextItems };
        }),
      updateItem: (id, updater) =>
        set((state) => ({
          items: state.items.map((item) => (item.id === id ? updater(item) : item)),
        })),
      removeItem: (id) =>
        set((state) => ({
          items: state.items.filter((item) => item.id !== id),
        })),
      clear: () => set({ items: [] }),
    }),
    {
      name: 'scholar-ai-upload-workspace',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        items: state.items.map(({ file: _file, ...item }) => item),
      }),
      merge: (persistedState, currentState) => {
        const persistedItems = ((persistedState as Partial<UploadWorkspaceState> | undefined)?.items ?? []) as PersistedUploadQueueItem[];
        return {
          ...currentState,
          ...(persistedState as Partial<UploadWorkspaceState>),
          items: persistedItems.map(normalizePersistedItem),
        };
      },
    }
  )
);
