import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SectionTree } from './SectionTree';

describe('SectionTree', () => {
  it('renders IMRaD ranges with page_start/page_end shape', () => {
    const onPageSelect = vi.fn();

    render(
      <SectionTree
        imrad={{
          introduction: { page_start: 1, page_end: 2 },
          methods: { page_start: 3, page_end: 6 },
        }}
        onPageSelect={onPageSelect}
        currentPage={1}
        isZh={true}
      />,
    );

    expect(screen.getByText('引言')).toBeInTheDocument();
    expect(screen.getByText('方法')).toBeInTheDocument();

    fireEvent.click(screen.getByText('方法'));
    expect(onPageSelect).toHaveBeenCalledWith(3);
  });

  it('renders sections from generic sections array shape', () => {
    render(
      <SectionTree
        imrad={{
          sections: [
            { title: 'Related Work', start: 4, end: 8 },
            { title: 'Experiments', page_start: 9, page_end: 12 },
          ],
        }}
        onPageSelect={() => {}}
        currentPage={10}
        isZh={false}
      />,
    );

    expect(screen.getByText('Related Work')).toBeInTheDocument();
    expect(screen.getByText('Experiments')).toBeInTheDocument();
  });

  it('shows fallback when no sections can be parsed', () => {
    render(
      <SectionTree
        imrad={null}
        onPageSelect={() => {}}
        currentPage={1}
        isZh={true}
      />,
    );

    expect(screen.getByText('暂无可导航章节，稍后可在完成解析后查看。')).toBeInTheDocument();
  });
});
