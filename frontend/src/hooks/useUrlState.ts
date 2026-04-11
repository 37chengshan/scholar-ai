/**
 * useUrlState Hook - URL State Synchronization
 *
 * Synchronizes component state with URL query parameters.
 * Enables state persistence across page refreshes and route navigation.
 *
 * Features:
 * - useState-like interface with automatic URL sync
 * - Support for string, number, boolean, and array types
 * - Support for optional values (undefined)
 * - Debounced URL updates to prevent excessive history entries
 * - Type-safe parameter parsing and serialization
 *
 * Usage:
 *   const [search, setSearch] = useUrlState('search', '');
 *   const [page, setPage] = useUrlState('page', 1);
 *   const [view, setView] = useUrlState<'a' | 'b'>('view', 'a');
 *   const [starred, setStarred] = useUrlStateOptional<boolean>('starred');
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router';

type UrlStateType = 'string' | 'number' | 'boolean' | 'array' | 'object';

interface UrlStateOptions {
  debounceMs?: number;
  replace?: boolean;
}

const DEFAULT_DEBOUNCE_MS = 100;

export function useUrlState<T extends string>(
  key: string,
  defaultValue: T extends '' ? string : T,
  options?: UrlStateOptions
): [T extends '' ? string : T, (value: T) => void];

export function useUrlState<T extends number>(
  key: string,
  defaultValue: T,
  options?: UrlStateOptions
): [T, (value: T) => void];

export function useUrlState<T extends boolean>(
  key: string,
  defaultValue: T,
  options?: UrlStateOptions
): [T, (value: T) => void];

export function useUrlState<T extends string | number | boolean>(
  key: string,
  defaultValue: T,
  options?: UrlStateOptions
): [T, (value: T) => void] {
  const type = inferType(defaultValue);
  const debounceMs = options?.debounceMs ?? DEFAULT_DEBOUNCE_MS;
  const replace = options?.replace ?? true;
  const [searchParams, setSearchParams] = useSearchParams();
  
  const getInitialState = (): T => {
    const paramValue = searchParams.get(key);
    if (paramValue === null || paramValue === '') {
      return defaultValue;
    }
    return parseValue(paramValue, type, defaultValue);
  };
  
  const [state, setState] = useState<T>(getInitialState);
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  
  useEffect(() => {
    const paramValue = searchParams.get(key);
    const parsedValue = paramValue === null || paramValue === '' 
      ? defaultValue 
      : parseValue(paramValue, type, defaultValue);
    
    setState(parsedValue);
  }, [key, searchParams.toString()]);
  
  const updateUrl = useCallback((value: T) => {
    const newParams = new URLSearchParams(searchParams);
    
    if (value === defaultValue) {
      newParams.delete(key);
    } else {
      const serialized = serializeValue(value, inferType(value));
      if (serialized) {
        newParams.set(key, serialized);
      } else {
        newParams.delete(key);
      }
    }
    
    setSearchParams(newParams, { replace });
  }, [key, searchParams.toString(), setSearchParams, defaultValue, replace]);
  
  const setStateWithUrl = useCallback((value: T) => {
    setState(value);
    
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    const timer = setTimeout(() => {
      updateUrl(value);
    }, debounceMs);
    
    setDebounceTimer(timer);
  }, [updateUrl, debounceMs, debounceTimer]);
  
  useEffect(() => {
    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
    };
  }, [debounceTimer]);
  
  return [state, setStateWithUrl];
}

/**
 * useUrlStateOptional - For optional values that can be undefined
 * 
 * When value is undefined, the URL parameter is removed.
 * When URL parameter is missing, returns undefined.
 */
export function useUrlStateOptional<T extends string | number | boolean>(
  key: string,
  defaultValue?: T | undefined
): [T | undefined, (value: T | undefined) => void] {
  const type = defaultValue !== undefined ? inferType(defaultValue) : 'string';
  const [searchParams, setSearchParams] = useSearchParams();
  
  const getInitialState = (): T | undefined => {
    const paramValue = searchParams.get(key);
    if (paramValue === null || paramValue === '' || paramValue === 'null') {
      return defaultValue;
    }
    if (defaultValue === undefined) {
      return paramValue as T;
    }
    return parseValue(paramValue, type, defaultValue);
  };
  
  const [state, setState] = useState<T | undefined>(getInitialState);
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  
  useEffect(() => {
    const paramValue = searchParams.get(key);
    let parsedValue: T | undefined;
    
    if (paramValue === null || paramValue === '' || paramValue === 'null') {
      parsedValue = defaultValue;
    } else if (defaultValue === undefined) {
      parsedValue = paramValue as T;
    } else {
      parsedValue = parseValue(paramValue, type, defaultValue);
    }
    
    setState(parsedValue);
  }, [key, searchParams.toString()]);
  
  const updateUrl = useCallback((value: T | undefined) => {
    const newParams = new URLSearchParams(searchParams);
    
    if (value === undefined || value === defaultValue) {
      newParams.delete(key);
    } else {
      const serialized = serializeValue(value, inferType(value));
      if (serialized) {
        newParams.set(key, serialized);
      } else {
        newParams.delete(key);
      }
    }
    
    setSearchParams(newParams, { replace: true });
  }, [key, searchParams.toString(), setSearchParams, defaultValue]);
  
  const setStateWithUrl = useCallback((value: T | undefined) => {
    setState(value);
    
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    const timer = setTimeout(() => {
      updateUrl(value);
    }, DEFAULT_DEBOUNCE_MS);
    
    setDebounceTimer(timer);
  }, [updateUrl, debounceTimer]);
  
  useEffect(() => {
    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
    };
  }, [debounceTimer]);
  
  return [state, setStateWithUrl];
}

function inferType(value: any): UrlStateType {
  if (typeof value === 'string') return 'string';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'boolean') return 'boolean';
  if (Array.isArray(value)) return 'array';
  if (typeof value === 'object' && value !== null) return 'object';
  return 'string';
}

function parseValue<T>(param: string, type: UrlStateType, defaultValue: T): T {
  try {
    switch (type) {
      case 'string':
        return param as T;
      
      case 'number':
        const num = parseFloat(param);
        return isNaN(num) ? defaultValue : num as T;
      
      case 'boolean':
        if (param === 'true' || param === '1') return true as T;
        if (param === 'false' || param === '0') return false as T;
        return defaultValue;
      
      case 'array':
        if (!param) return defaultValue;
        try {
          const parsed = JSON.parse(param);
          return Array.isArray(parsed) ? parsed as T : defaultValue;
        } catch {
          return param.split(',').filter(Boolean) as T;
        }
      
      case 'object':
        if (!param) return defaultValue;
        try {
          const parsed = JSON.parse(param);
          return typeof parsed === 'object' && parsed !== null ? parsed as T : defaultValue;
        } catch {
          return defaultValue;
        }
      
      default:
        return param as T;
    }
  } catch {
    return defaultValue;
  }
}

function serializeValue<T>(value: T, type: UrlStateType): string | null {
  if (value === null || value === undefined) return null;
  
  switch (type) {
    case 'string':
      return value as string;
    
    case 'number':
      return String(value);
    
    case 'boolean':
      return value ? 'true' : 'false';
    
    case 'array':
      const arr = value as string[];
      if (arr.length === 0) return null;
      return JSON.stringify(arr);
    
    case 'object':
      const obj = value as Record<string, any>;
      if (Object.keys(obj).length === 0) return null;
      return JSON.stringify(obj);
    
    default:
      return String(value);
  }
}