/**
 * useProjects Hook - Projects State Management
 *
 * Custom hook for managing projects with:
 * - List projects with paper counts
 * - Create new project
 * - Update project
 * - Delete project
 * - Assign paper to project
 */

import { useState, useEffect, useCallback } from 'react';
import * as projectsApi from '@/services/projectsApi';
import type { Project } from '@/services/projectsApi';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Hook return type
 */
interface UseProjectsReturn {
  projects: Project[];
  loading: boolean;
  error: string | null;
  createProject: (name: string, color?: string) => Promise<Project | null>;
  updateProject: (id: string, data: { name?: string; color?: string }) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  assignPaper: (paperId: string, projectId: string | null) => Promise<void>;
  refetch: () => Promise<void>;
}

/**
 * useProjects Hook
 *
 * Manages projects list and CRUD operations.
 *
 * @returns Projects state and actions
 */
export function useProjects(): UseProjectsReturn {
  const { user } = useAuth();

  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch projects from API
   */
  const fetchProjects = useCallback(async () => {
    if (!user) {
      setProjects([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch (err: any) {
      setError(err.response?.data?.error?.detail || err.message || 'Failed to fetch projects');
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  /**
   * Create new project
   */
  const createProject = useCallback(async (name: string, color?: string): Promise<Project | null> => {
    try {
      setError(null);
      const newProject = await projectsApi.create(name, color);
      await fetchProjects(); // Refresh list
      return newProject;
    } catch (err: any) {
      setError(err.response?.data?.error?.detail || err.message || 'Failed to create project');
      return null;
    }
  }, [fetchProjects]);

  /**
   * Update project
   */
  const updateProject = useCallback(async (id: string, data: { name?: string; color?: string }): Promise<void> => {
    try {
      setError(null);
      await projectsApi.update(id, data);
      await fetchProjects(); // Refresh list
    } catch (err: any) {
      setError(err.response?.data?.error?.detail || err.message || 'Failed to update project');
    }
  }, [fetchProjects]);

  /**
   * Delete project
   */
  const deleteProject = useCallback(async (id: string): Promise<void> => {
    try {
      setError(null);
      await projectsApi.deleteProject(id);
      await fetchProjects(); // Refresh list
    } catch (err: any) {
      setError(err.response?.data?.error?.detail || err.message || 'Failed to delete project');
    }
  }, [fetchProjects]);

  /**
   * Assign paper to project
   */
  const assignPaper = useCallback(async (paperId: string, projectId: string | null): Promise<void> => {
    try {
      setError(null);
      await projectsApi.assignPaper(paperId, projectId);
      await fetchProjects(); // Refresh list to update paper counts
    } catch (err: any) {
      setError(err.response?.data?.error?.detail || err.message || 'Failed to assign paper');
    }
  }, [fetchProjects]);

  /**
   * Manual refetch
   */
  const refetch = useCallback(async () => {
    await fetchProjects();
  }, [fetchProjects]);

  return {
    projects,
    loading,
    error,
    createProject,
    updateProject,
    deleteProject,
    assignPaper,
    refetch,
  };
}

export type { UseProjectsReturn };