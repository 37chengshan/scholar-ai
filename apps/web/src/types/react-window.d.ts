declare module 'react-window' {
  import * as React from 'react';

  export interface ListChildComponentProps<T = unknown> {
    index: number;
    style: React.CSSProperties;
    data: T;
  }

  export interface FixedSizeListProps<T = unknown> {
    children: React.ComponentType<ListChildComponentProps<T>>;
    height: number;
    itemCount: number;
    itemData: T;
    itemKey?: (index: number, data: T) => React.Key;
    itemSize: number;
    width: number | string;
    overscanCount?: number;
    onItemsRendered?: (props: {
      overscanStartIndex: number;
      overscanStopIndex: number;
      visibleStartIndex: number;
      visibleStopIndex: number;
    }) => void;
    className?: string;
  }

  export class FixedSizeList<T = unknown> extends React.Component<FixedSizeListProps<T>> {
    scrollToItem(index: number, align?: 'auto' | 'smart' | 'center' | 'end' | 'start'): void;
  }

  export interface VariableSizeListProps<T = unknown> {
    children: React.ComponentType<ListChildComponentProps<T>>;
    height: number;
    itemCount: number;
    itemData: T;
    itemKey?: (index: number, data: T) => React.Key;
    itemSize: (index: number) => number;
    width: number | string;
    overscanCount?: number;
    estimatedItemSize?: number;
    onItemsRendered?: (props: {
      overscanStartIndex: number;
      overscanStopIndex: number;
      visibleStartIndex: number;
      visibleStopIndex: number;
    }) => void;
    onScroll?: (props: {
      scrollDirection: 'forward' | 'backward';
      scrollOffset: number;
      scrollUpdateWasRequested: boolean;
    }) => void;
    className?: string;
  }

  export class VariableSizeList<T = unknown> extends React.Component<VariableSizeListProps<T>> {
    scrollToItem(index: number, align?: 'auto' | 'smart' | 'center' | 'end' | 'start'): void;
    scrollTo(scrollOffset: number): void;
    resetAfterIndex(index: number, shouldForceUpdate?: boolean): void;
    resetAfterIndices?: (indices: { index: number; shouldForceUpdate?: boolean }[]) => void;
  }
}
