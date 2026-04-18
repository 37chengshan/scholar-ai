import { create } from 'zustand';

export type UploadQueueStatus =
  | 'pending'
  | 'preparing'
  | 'uploading'
  | 'queued'
  | 'completed'
  | 'failed';

export interface UploadQueueItem {
  id: string;
  file: File;
  fileName: string;
  sizeBytes: number;
  progress: number;
  status: UploadQueueStatus;
  error?: string;
  importJobId?: string;
  uploadSessionId?: string;
}

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

export const useUploadWorkspaceStore = create<UploadWorkspaceState>((set) => ({
  items: [],
  addFiles: (files) =>
    set((state) => ({
      items: [
        ...state.items,
        ...files.map((file) => ({
          id: createUploadId(),
          file,
          fileName: file.name,
          sizeBytes: file.size,
          progress: 0,
          status: 'pending' as const,
        })),
      ],
    })),
  updateItem: (id, updater) =>
    set((state) => ({
      items: state.items.map((item) => (item.id === id ? updater(item) : item)),
    })),
  removeItem: (id) =>
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
    })),
  clear: () => set({ items: [] }),
}));
