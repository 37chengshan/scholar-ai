import type { HttpClient } from '../client/http';
import type {
  CreateNoteDto,
  NoteDto,
  SaveEvidenceNoteRequestDto,
  UpdateNoteDto,
} from '@scholar-ai/types';

export interface NotesApi {
  list: (params?: Record<string, unknown>) => Promise<{ notes: NoteDto[]; total: number; limit?: number; offset?: number }>;
  get: (noteId: string) => Promise<NoteDto>;
  create: (payload: CreateNoteDto) => Promise<NoteDto>;
  update: (noteId: string, payload: UpdateNoteDto) => Promise<NoteDto>;
  remove: (noteId: string) => Promise<void>;
  saveEvidence: (payload: SaveEvidenceNoteRequestDto) => Promise<NoteDto>;
}

export function createNotesApi(client: HttpClient): NotesApi {
  return {
    list: (params) => client.get<{ notes: NoteDto[]; total: number; limit?: number; offset?: number }>('/api/v1/notes', { params }),
    get: (noteId) => client.get<NoteDto>(`/api/v1/notes/${noteId}`),
    create: (payload) => client.post<NoteDto>('/api/v1/notes', payload),
    update: (noteId, payload) => client.put<NoteDto>(`/api/v1/notes/${noteId}`, payload),
    remove: async (noteId) => {
      await client.delete<void>(`/api/v1/notes/${noteId}`);
    },
    saveEvidence: (payload) => client.post<NoteDto>('/api/v1/notes/evidence', payload),
  };
}
