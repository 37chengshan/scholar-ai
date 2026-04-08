/**
 * Notes API Service
 *
 * Notes management API calls:
 * - getNotes(): Get notes with optional filtering
 * - getNote(): Get specific note
 * - createNote(): Create new note
 * - updateNote(): Update existing note
 * - deleteNote(): Delete note
 *
 * Supports cross-paper association via paperIds array.
 * All endpoints require authentication.
 */

import apiClient from '@/utils/apiClient';

/**
 * Note type from backend
 */
export interface Note {
  id: string;
  userId: string;
  title: string;
  content: string;
  tags: string[];
  paperIds: string[];
  createdAt: string;
  updatedAt: string;
}

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
export interface CreateNotePayload {
  title: string;
  content: string;
  tags?: string[];
  paperIds?: string[];
}

/**
 * Update note payload
 */
export interface UpdateNotePayload {
  title?: string;
  content?: string;
  tags?: string[];
  paperIds?: string[];
}

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
  const response = await apiClient.get<Note[]>('/api/notes', {
    params: {
      paperId: params?.paperId,
      tag: params?.tag,
      sortBy: params?.sortBy || 'createdAt',
      order: params?.order || 'desc',
      limit: params?.limit,
      offset: params?.offset,
    },
  });

  return response.data;
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
  const response = await apiClient.get<Note>(`/api/notes/${id}`);
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
  const response = await apiClient.post<Note>('/api/notes', payload);
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
  const response = await apiClient.put<Note>(`/api/notes/${id}`, payload);
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
  await apiClient.delete(`/api/notes/${id}`);
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
  const response = await apiClient.get<Note[]>(`/api/notes/paper/${paperId}`);
  return response.data;
}