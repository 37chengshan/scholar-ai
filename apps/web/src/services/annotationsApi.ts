/**
 * Annotation management API calls with backend field normalization.
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

interface RawAnnotation {
  id: string;
  paper_id: string;
  user_id: string;
  type: 'highlight' | 'note' | 'bookmark';
  page_number: number;
  position: any;
  content?: string | null;
  color?: string;
  created_at: string;
  updated_at: string;
}

function normalizeAnnotation(annotation: RawAnnotation): Annotation {
  return {
    id: annotation.id,
    paperId: annotation.paper_id,
    userId: annotation.user_id,
    type: annotation.type,
    pageNumber: annotation.page_number,
    position: annotation.position,
    content: annotation.content ?? null,
    color: annotation.color,
    createdAt: annotation.created_at,
    updatedAt: annotation.updated_at,
  };
}

/** List annotations for a paper */
export async function list(paperId: string): Promise<Annotation[]> {
  const response = await apiClient.get<RawAnnotation[]>(`/api/v1/annotations/${paperId}`);
  return (response.data || []).map(normalizeAnnotation);
}

/** Create annotation */
export async function create(data: CreateAnnotationData): Promise<Annotation> {
  const response = await apiClient.post<RawAnnotation>('/api/v1/annotations', data);
  return normalizeAnnotation(response.data);
}

/** Update annotation */
export async function update(id: string, data: UpdateAnnotationData): Promise<Annotation> {
  const response = await apiClient.patch<RawAnnotation>(`/api/v1/annotations/${id}`, data);
  return normalizeAnnotation(response.data);
}

/** Delete annotation */
export async function deleteAnnotation(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/annotations/${id}`);
}
