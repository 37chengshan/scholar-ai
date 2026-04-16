/**
 * useAutocomplete Hook
 *
 * Autocomplete state management with debouncing and minimum character threshold.
 *
 * Features:
 * - Debounced search query (300ms delay per D-01)
 * - Minimum 3 characters before fetching (per D-01)
 * - Loading and error states
 * - Clear function to reset state
 *
 * Per D-01: Triggers at >=3 characters
 * Per D-04: Results cached by backend (1h TTL)
 */

import { useState, useEffect, useCallback } from 'react';
import { autocomplete, AutocompletePaper } from '@/services/searchApi';

interface UseAutocompleteOptions {
  minChars?: number;   // D-01: Default 3
  debounceMs?: number; // D-01: Default 300ms
  limit?: number;      // D-03: Default 5
}

interface UseAutocompleteReturn {
  query: string;
  setQuery: (query: string) => void;
  results: AutocompletePaper[];
  loading: boolean;
  error: string | null;
  clear: () => void;
}

/**
 * useAutocomplete hook with debounce and minimum character threshold
 *
 * @param options - Configuration options
 * @returns Autocomplete state and handlers
 */
export function useAutocomplete(options: UseAutocompleteOptions = {}): UseAutocompleteReturn {
  const { minChars = 3, debounceMs = 300, limit = 5 } = options;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AutocompletePaper[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // D-01: Only search if query has >=3 characters
    if (query.length < minChars) {
      setResults([]);
      return;
    }

    const timeoutId = setTimeout(async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await autocomplete(query, limit);
        setResults(data);
      } catch (err: any) {
        setError(err.message || 'Autocomplete failed');
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, debounceMs);

    return () => clearTimeout(timeoutId);
  }, [query, minChars, debounceMs, limit]);

  const clear = useCallback(() => {
    setQuery('');
    setResults([]);
    setError(null);
  }, []);

  return { query, setQuery, results, loading, error, clear };
}