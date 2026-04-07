/**
 * Search API Types
 * Types for Semantic Scholar autocomplete and author search APIs
 */

/**
 * Autocomplete response - paper suggestions
 */
export interface AutocompletePaper {
  paperId: string;
  title: string;
  year?: number;
  authors?: Array<{
    authorId: string;
    name: string;
  }>;
}

/**
 * Author search result
 */
export interface AuthorSearchResult {
  authorId: string;
  name: string;
  hIndex?: number;
  citationCount?: number;
  paperCount?: number;
}

/**
 * Author papers response
 */
export interface AuthorPaper {
  paperId: string;
  title: string;
  year?: number;
  citationCount?: number;
}

/**
 * Author papers API response with pagination
 */
export interface AuthorPapersResponse {
  data: AuthorPaper[];
  next?: number; // Offset for next page
}

/**
 * Author search API response
 */
export interface AuthorSearchResponse {
  data: AuthorSearchResult[];
  total?: number;
}

/**
 * Autocomplete API response
 */
export interface AutocompleteResponse {
  data: AutocompletePaper[];
}