import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Search } from './Search';

vi.mock('@/features/search/components/SearchWorkspace', () => ({
  SearchWorkspace: () => <div data-testid="search-workspace">search-workspace</div>,
}));

describe('Search page shell', () => {
  it('renders search workspace container', () => {
    render(<Search />);
    expect(screen.getByTestId('search-workspace')).toBeInTheDocument();
  });
});
