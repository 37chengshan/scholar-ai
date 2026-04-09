/**
 * useAutoSave Hook
 *
 * Auto-save hook with debounce and IndexedDB fallback:
 * - Debounces content changes by specified interval (default 1000ms)
 * - Returns save status: idle | saving | saved | error
 * - Falls back to IndexedDB when API save fails
 * - Retries IndexedDB queued saves on reconnect
 *
 * Requirements: NOTE-03
 */

import { useState, useRef, useCallback, useEffect } from 'react';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface UseAutoSaveOptions {
  content: any;
  onSave: (content: any) => Promise<void>;
  debounceMs?: number;
  noteId?: string;
}

interface UseAutoSaveReturn {
  status: SaveStatus;
  lastSaved: Date | null;
  retrySave: () => void;
}

const DB_NAME = 'ScholarAI_Notes';
const DB_VERSION = 1;
const STORE_NAME = 'drafts';

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
  });
}

async function saveToIndexedDB(key: string, value: any): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.put(value, key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function getFromIndexedDB(key: string): Promise<any | undefined> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(key);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function removeFromIndexedDB(key: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.delete(key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export function useAutoSave({
  content,
  onSave,
  debounceMs = 1000,
  noteId,
}: UseAutoSaveOptions): UseAutoSaveReturn {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const contentRef = useRef(content);

  // Keep contentRef in sync
  useEffect(() => {
    contentRef.current = content;
  }, [content]);

  const performSave = useCallback(async (contentToSave: any) => {
    setStatus('saving');
    try {
      await onSave(contentToSave);
      setStatus('saved');
      setLastSaved(new Date());
      // Clear IndexedDB draft on successful save
      if (noteId) {
        await removeFromIndexedDB(`note_draft_${noteId}`);
      }
    } catch {
      setStatus('error');
      // Fallback to IndexedDB
      if (noteId) {
        try {
          await saveToIndexedDB(`note_draft_${noteId}`, contentToSave);
        } catch (dbError) {
          console.error('Failed to save to IndexedDB:', dbError);
        }
      }
    }
  }, [onSave, noteId]);

  // Debounced save on content change
  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      performSave(content);
    }, debounceMs);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [content, debounceMs, performSave]);

  // Reconnect sync: flush IndexedDB drafts when coming back online
  useEffect(() => {
    const handleOnline = async () => {
      if (noteId) {
        const draft = await getFromIndexedDB(`note_draft_${noteId}`);
        if (draft !== undefined) {
          setStatus('saving');
          try {
            await onSave(draft);
            setStatus('saved');
            setLastSaved(new Date());
            await removeFromIndexedDB(`note_draft_${noteId}`);
          } catch {
            setStatus('error');
          }
        }
      }
    };

    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, [noteId, onSave]);

  const retrySave = useCallback(() => {
    performSave(contentRef.current);
  }, [performSave]);

  return { status, lastSaved, retrySave };
}
