import apiClient from '@/utils/apiClient';
import type {
  CreateNoteDto,
  NoteDto,
  SaveEvidenceNoteRequestDto,
  UpdateNoteDto,
} from '@scholar-ai/types';

export type Note = NoteDto;

/**
 * Get notes query parameters
 */
export interface GetNotesParams {
  paperId?: string;
  tag?: string;
  sortBy?: 'createdAt' | 'updatedAt' | 'title';
  order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

/**
 * Create note payload
 */
export type CreateNotePayload = CreateNoteDto;

/**
 * Update note payload
 */
export type UpdateNotePayload = UpdateNoteDto;
export type SaveEvidenceNotePayload = SaveEvidenceNoteRequestDto;

/**
 * Get notes list with optional filtering
 *
 * GET /api/notes
 * Returns user's notes with optional filters
 *
 * @param params - Query parameters (paperId, tag, sortBy, order)
 * @returns Notes array
 */
export async function getNotes(params?: GetNotesParams): Promise<Note[]> {
  const response = await apiClient.get<{
    notes: Note[];
    total: number;
    limit: number;
    offset: number;
  }>('/api/v1/notes', {
    params: {
      paperId: params?.paperId,
      tag: params?.tag,
      sortBy: params?.sortBy || 'createdAt',
      order: params?.order || 'desc',
      limit: params?.limit,
      offset: params?.offset,
    },
  });

  // Backend returns { notes: [...], total, limit, offset }
  return response.data.notes || [];
}

/**
 * Get specific note
 *
 * GET /api/notes/:id
 * Returns single note details
 *
 * @param id - Note ID
 * @returns Note details
 */
export async function getNote(id: string): Promise<Note> {
  const response = await apiClient.get<Note>(`/api/v1/notes/${id}`);
  return response.data;
}

/**
 * Create new note
 *
 * POST /api/notes
 * Creates note with optional paper associations
 *
 * @param payload - Note creation data
 * @returns Created note
 */
export async function createNote(payload: CreateNotePayload): Promise<Note> {
  const response = await apiClient.post<Note>('/api/v1/notes', payload);
  return response.data;
}

/**
 * Update existing note
 *
 * PUT /api/notes/:id
 * Updates note fields (partial update supported)
 *
 * @param id - Note ID
 * @param payload - Note update data
 * @returns Updated note
 */
export async function updateNote(id: string, payload: UpdateNotePayload): Promise<Note> {
  const response = await apiClient.put<Note>(`/api/v1/notes/${id}`, payload);
  return response.data;
}

/**
 * Delete note
 *
 * DELETE /api/notes/:id
 * Permanently removes note
 *
 * @param id - Note ID
 */
export async function deleteNote(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/notes/${id}`);
}

/**
 * Get notes for specific paper (legacy endpoint)
 *
 * GET /api/notes/paper/:paperId
 * Returns all notes associated with a paper
 *
 * @param paperId - Paper ID
 * @returns Notes array
 */
export async function getNotesByPaper(paperId: string): Promise<Note[]> {
  const response = await apiClient.get<{
    notes: Note[];
    total: number;
  }>(`/api/v1/notes/paper/${paperId}`);
  return response.data.notes || [];
}

/**
 * Save evidence block into note system.
 */
export async function saveEvidenceNote(payload: SaveEvidenceNotePayload): Promise<Note> {
  const response = await apiClient.post<Note>('/api/v1/notes/evidence', payload);
  return response.data;
}
