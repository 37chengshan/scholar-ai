/**
 * VirtualizedMessageList - VariableSizeList wrapper for chat message feed
 *
 * Uses react-window VariableSizeList to render only visible messages in the DOM,
 * reducing DOM node count from O(n) to O(overscan) for long conversations.
 *
 * - < 20 messages uses fast-path .map() in MessageFeed
 * - >= 20 messages switches to this virtualized renderer
 * - Streaming messages use ResizeObserver for dynamic height
 * - Completed messages use measureText pre-estimation
 */

import { useRef, useCallback, useEffect, useMemo, type ReactNode } from 'react';
import { VariableSizeList, type ListChildComponentProps } from 'react-window';
import type { ChatRenderMessage } from '@/features/chat/hooks/useChatMessagesViewModel';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { ThinkingStep } from '@/app/components/ThinkingProcess';
import type { CitationItem, ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

const VIRTUALIZATION_THRESHOLD = 20;
const FALLBACK_ITEM_HEIGHT = 200;
const OVERSCAN_COUNT = 5;

interface VirtualizedItemData {
  messages: ChatRenderMessage[];
  renderMessage: (message: ChatRenderMessage, index: number) => ReactNode;
}

interface VirtualizedMessageListProps {
  renderMessages: ChatRenderMessage[];
  measuredHeights: Record<string, number>;
  height: number;
  /** Render function for a single message item */
  renderItem: (message: ChatRenderMessage, index: number) => ReactNode;
  /** Callback when visible range changes (for pinned-bottom detection) */
  onItemsRendered?: (props: {
    overscanStartIndex: number;
    overscanStopIndex: number;
    visibleStartIndex: number;
    visibleStopIndex: number;
  }) => void;
  /** Ref to expose list methods */
  listRef?: React.RefObject<VariableSizeList<VirtualizedItemData> | null>;
  /** Index of the streaming message, used for dynamic height reset */
  streamingMessageIndex?: number;
}

/**
 * Returns the estimated height for a message at the given index.
 */
function getItemSize(
  measuredHeights: Record<string, number>,
  messages: ChatRenderMessage[],
  index: number,
): number {
  const message = messages[index];
  if (!message) {
    return FALLBACK_ITEM_HEIGHT;
  }
  return measuredHeights[message.id] || FALLBACK_ITEM_HEIGHT;
}

/**
 * Item renderer that wraps the parent's renderItem in a div with proper
 * sizing and accessibility attributes.
 */
function VirtualizedItem({
  index,
  style,
  data,
}: ListChildComponentProps<VirtualizedItemData>) {
  const { messages, renderMessage } = data;
  const message = messages[index];

  if (!message) {
    return <div style={style} />;
  }

  return (
    <div
      style={style}
      role="article"
      aria-label={`${message.role === 'assistant' ? 'ScholarAI' : 'User'}: ${message.displayContent?.slice(0, 80) ?? ''}`}
      data-message-id={message.id}
    >
      {renderMessage(message, index)}
    </div>
  );
}

export function VirtualizedMessageList({
  renderMessages,
  measuredHeights,
  height,
  renderItem,
  onItemsRendered,
  listRef: externalListRef,
  streamingMessageIndex,
}: VirtualizedMessageListProps) {
  const internalListRef = useRef<VariableSizeList<VirtualizedItemData> | null>(null);
  const listRef = externalListRef ?? internalListRef;
  // Cast needed: react-window LegacyRef vs React 18 RefObject
  const listRefCallback = useCallback(
    (instance: VariableSizeList<VirtualizedItemData> | null) => {
      (listRef as React.MutableRefObject<VariableSizeList<VirtualizedItemData> | null>).current = instance;
    },
    [listRef],
  );

  const itemData = useMemo(() => ({
    messages: renderMessages,
    renderMessage: renderItem,
  }), [renderMessages, renderItem]);

  const itemSizeCallback = useCallback(
    (index: number) => getItemSize(measuredHeights, renderMessages, index),
    [measuredHeights, renderMessages],
  );

  // Reset the list when streaming message index changes to recalculate heights
  useEffect(() => {
    if (
      streamingMessageIndex !== undefined
      && streamingMessageIndex >= 0
      && listRef.current
    ) {
      listRef.current.resetAfterIndex(streamingMessageIndex, false);
    }
  }, [streamingMessageIndex, measuredHeights, listRef]);

  return (
    <VariableSizeList<VirtualizedItemData>
      ref={listRefCallback}
      height={height}
      itemCount={renderMessages.length}
      itemData={itemData}
      itemSize={itemSizeCallback}
      width="100%"
      overscanCount={OVERSCAN_COUNT}
      estimatedItemSize={FALLBACK_ITEM_HEIGHT}
      onItemsRendered={onItemsRendered}
      className="virtualized-message-list"
    >
      {VirtualizedItem}
    </VariableSizeList>
  );
}

export { VIRTUALIZATION_THRESHOLD, FALLBACK_ITEM_HEIGHT, OVERSCAN_COUNT };
