/**
 * NoteFolderTree Component
 *
 * Displays a 2-level folder tree for organizing notes.
 * Supports: expand/collapse, select folder, create folder (max 2 levels).
 *
 * Requirements: NOTE-06
 */

import { useState, useCallback } from 'react';
import { ChevronRight, ChevronDown, FolderPlus, Folder } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { clsx } from 'clsx';

export interface NoteFolder {
  id: string;
  name: string;
  parentId: string | null;
  noteCount: number;
}

interface NoteFolderTreeProps {
  folders: NoteFolder[];
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onCreateFolder: (name: string, parentId: string | null) => void;
}

export function NoteFolderTree({
  folders,
  selectedFolderId,
  onSelectFolder,
  onCreateFolder,
}: NoteFolderTreeProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [creatingIn, setCreatingIn] = useState<string | null>(null);
  const [newFolderName, setNewFolderName] = useState('');

  // Build tree structure (max 2 levels)
  const rootFolders = folders.filter((f) => f.parentId === null);
  const getChildFolders = (parentId: string) =>
    folders.filter((f) => f.parentId === parentId);

  const toggleExpand = useCallback((folderId: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  }, []);

  const handleCreateSubmit = useCallback(
    (parentId: string | null) => {
      if (newFolderName.trim()) {
        onCreateFolder(newFolderName.trim(), parentId);
        setNewFolderName('');
        setCreatingIn(null);
        if (parentId) {
          setExpandedFolders((prev) => new Set(prev).add(parentId));
        }
      }
    },
    [newFolderName, onCreateFolder]
  );

  const renderFolder = (folder: NoteFolder, depth: number) => {
    const children = getChildFolders(folder.id);
    const isExpanded = expandedFolders.has(folder.id);
    const isSelected = selectedFolderId === folder.id;
    const hasChildren = children.length > 0;
    const canAddChild = depth < 1; // Max 2 levels: root (0) + child (1)

    return (
      <div key={folder.id}>
        <div
          className={clsx(
            'flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors',
            isSelected && 'bg-muted/80 font-medium',
            !isSelected && 'hover:bg-muted/50'
          )}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
          onClick={() => onSelectFolder(folder.id)}
        >
          {hasChildren ? (
            <button
              className="p-0.5 hover:bg-muted/50 rounded"
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(folder.id);
              }}
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-3 h-3 text-muted-foreground" />
              )}
            </button>
          ) : (
            <span className="w-4" />
          )}
          <Folder className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
          <span className="truncate flex-1">{folder.name}</span>
          <span className="text-[10px] text-muted-foreground/60 flex-shrink-0">
            {folder.noteCount}
          </span>
          {canAddChild && (
            <button
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-muted/50 rounded"
              onClick={(e) => {
                e.stopPropagation();
                setCreatingIn(folder.id);
                setNewFolderName('');
              }}
            >
              <FolderPlus className="w-3 h-3 text-muted-foreground" />
            </button>
          )}
        </div>

        {/* Child folders */}
        {isExpanded && hasChildren && (
          <div>
            {children.map((child) => renderFolder(child, depth + 1))}
          </div>
        )}

        {/* Inline folder creation */}
        {creatingIn === folder.id && (
          <div className="flex items-center gap-1 px-2 py-1" style={{ paddingLeft: `${(depth + 1) * 12 + 8}px` }}>
            <Input
              autoFocus
              placeholder="文件夹名称"
              className="h-6 text-xs"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateSubmit(folder.id);
                if (e.key === 'Escape') setCreatingIn(null);
              }}
              onBlur={() => handleCreateSubmit(folder.id)}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="py-1">
      {/* "All Notes" root item */}
      <div
        className={clsx(
          'flex items-center gap-1.5 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors',
          selectedFolderId === null && 'bg-muted/80 font-medium',
          selectedFolderId !== null && 'hover:bg-muted/50'
        )}
        onClick={() => onSelectFolder(null)}
      >
        <Folder className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="flex-1">全部笔记</span>
      </div>

      {/* Root folders */}
      {rootFolders.map((folder) => renderFolder(folder, 0))}

      {/* Create root folder button */}
      {creatingIn === '__root__' ? (
        <div className="flex items-center gap-1 px-2 py-1">
          <Input
            autoFocus
            placeholder="文件夹名称"
            className="h-6 text-xs"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateSubmit(null);
              if (e.key === 'Escape') setCreatingIn(null);
            }}
            onBlur={() => handleCreateSubmit(null)}
          />
        </div>
      ) : (
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-1.5 h-7 text-xs text-muted-foreground"
          onClick={() => setCreatingIn('__root__')}
        >
          <FolderPlus className="w-3 h-3" />
          新建文件夹
        </Button>
      )}
    </div>
  );
}
