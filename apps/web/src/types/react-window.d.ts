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
  }

  export class FixedSizeList<T = unknown> extends React.Component<FixedSizeListProps<T>> {
    scrollToItem(index: number, align?: 'auto' | 'smart' | 'center' | 'end' | 'start'): void;
  }
}