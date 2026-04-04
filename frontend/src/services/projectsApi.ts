/**
 * Projects API Service
 *
 * Project management API calls:
 * - list(): Get user's projects
 * - create(): Create new project
 * - update(): Update project name/color
 * - delete(): Delete project
 * - assignPaper(): Assign paper to project
 */

import apiClient from '@/utils/apiClient';

/**
 * Project entity
 */
export interface Project {
  id: string;
  name: string;
  color: string;
  paperCount: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * Get user's projects
 *
 * GET /api/projects
 * Returns list of user's projects with paper counts
 *
 * @returns Projects list
 */
export async function list(): Promise<Project[]> {
  const response = await apiClient.get<{
    success: boolean;
    data: Project[];
  }>('/api/projects');

  return response.data.data;
}

/**
 * Create new project
 *
 * POST /api/projects
 * Creates a new project with name and optional color
 *
 * @param name - Project name
 * @param color - Project color (hex format, optional)
 * @returns Created project
 */
export async function create(name: string, color?: string): Promise<Project> {
  const response = await apiClient.post<{
    success: boolean;
    data: Project;
  }>('/api/projects', {
    name,
    color,
  });

  return response.data.data;
}

/**
 * Update project
 *
 * PATCH /api/projects/:id
 * Updates project name or color
 *
 * @param id - Project ID
 * @param data - Fields to update
 * @returns Updated project
 */
export async function update(id: string, data: { name?: string; color?: string }): Promise<Project> {
  const response = await apiClient.patch<{
    success: boolean;
    data: Project;
  }>(`/api/projects/${id}`, data);

  return response.data.data;
}

/**
 * Delete project
 *
 * DELETE /api/projects/:id
 * Removes project (papers remain, projectId set to null)
 *
 * @param id - Project ID
 */
export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}

/**
 * Assign paper to project
 *
 * PATCH /api/projects/paper/:paperId
 * Sets paper's projectId (or null to remove)
 *
 * @param paperId - Paper ID
 * @param projectId - Project ID (or null to unassign)
 * @returns Updated paper
 */
export async function assignPaper(paperId: string, projectId: string | null): Promise<{
  id: string;
  title: string;
  projectId: string | null;
}> {
  const response = await apiClient.patch<{
    success: boolean;
    data: {
      id: string;
      title: string;
      projectId: string | null;
    };
  }>(`/api/projects/paper/${paperId}`, {
    projectId,
  });

  return response.data.data;
}