/**
 * Annotations API Service
 *
 * Annotation management API calls:
 * - list(): Get annotations for a paper
 * - create(): Create new annotation (highlight, note, bookmark)
 * - update(): Update annotation content or color
 * - delete(): Delete annotation
 *
 * All endpoints require authentication.
 */

import apiClient from '@/utils/apiClient';

export interface Annotation {
  id: string;
  paperId: string;
  userId: string;
  type: 'highlight' | 'note' | 'bookmark';
  pageNumber: number;
  position: any;
  content?: string | null;
  color?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAnnotationData {
  paperId: string;
  type: 'highlight' | 'note' | 'bookmark';
  pageNumber: number;
  position: any;
  content?: string;
  color?: string;
}

export interface UpdateAnnotationData {
  content?: string;
  color?: string;
}

/**
 * List annotations for a paper
 *
 * GET /api/annotations/:paperId
 * Returns all annotations for a paper by the current user
 *
 * @param paperId - Paper ID
 * @returns Array of annotations
 */
export async function list(paperId: string): Promise<Annotation[]> {
  const response = await apiClient.get<{
    success: boolean;
    data: Annotation[];
  }>(`/api/v1/annotations/${paperId}`);

  return response.data.data;
}

/**
 * Create annotation
 *
 * POST /api/annotations
 * Creates a new annotation (highlight, note, or bookmark)
 *
 * @param data - Annotation data
 * @returns Created annotation
 */
export async function create(data: CreateAnnotationData): Promise<Annotation> {
  const response = await apiClient.post<{
    success: boolean;
    data: Annotation;
  }>('/api/v1/annotations', data);

  return response.data.data;
}

/**
 * Update annotation
 *
 * PATCH /api/annotations/:id
 * Updates annotation content or color
 *
 * @param id - Annotation ID
 * @param data - Update data
 * @returns Updated annotation
 */
export async function update(id: string, data: UpdateAnnotationData): Promise<Annotation> {
  const response = await apiClient.patch<{
    success: boolean;
    data: Annotation;
  }>(`/api/v1/annotations/${id}`, data);

  return response.data.data;
}

/**
 * Delete annotation
 *
 * DELETE /api/annotations/:id
 * Removes annotation permanently
 *
 * @param id - Annotation ID
 */
export async function deleteAnnotation(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/annotations/${id}`);
}