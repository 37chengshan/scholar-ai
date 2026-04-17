export interface PaperDto {
  id: string;
  title: string;
  authors: string[];
  year?: number | null;
  abstract?: string | null;
  doi?: string | null;
  arxivId?: string | null;
}
