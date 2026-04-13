/**
 * SSE Parser Utility Tests
 *
 * Tests for:
 * - parseSSELine: Single event parsing
 * - parseSSEStream: Multiple events parsing
 * - createSSEParser: EventSource integration
 * - validateEventContract: Contract validation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  parseSSELine,
  parseSSEStream,
  createSSEParser,
  validateEventContract,
  toSSEEvent,
  LastEventIdTracker,
  ContractViolationError,
  EVENT_CONTRACTS,
  ParsedSSEEvent,
} from './sseParser';
import { SSEEventType } from '../services/sseService';

describe('parseSSELine', () => {
  it('parses standard SSE event with id, event, and data', () => {
    const sseText = `id: abc123
event: thought
data: {"content":"Thinking about the query...","timestamp":"2024-01-15T10:30:00Z"}`;

    const result = parseSSELine(sseText);

    expect(result).not.toBeNull();
    expect(result?.id).toBe('abc123');
    expect(result?.type).toBe('thought');
    expect(result?.data).toEqual({
      content: 'Thinking about the query...',
      timestamp: '2024-01-15T10:30:00Z',
    });
  });

  it('parses SSE event without id', () => {
    const sseText = `event: message
data: {"content":"Final response","timestamp":"2024-01-15T10:31:00Z"}`;

    const result = parseSSELine(sseText);

    expect(result).not.toBeNull();
    expect(result?.id).toBeUndefined();
    expect(result?.type).toBe('message');
    expect(result?.data).toEqual({
      content: 'Final response',
      timestamp: '2024-01-15T10:31:00Z',
    });
  });

  it('handles tool_call event with tool field', () => {
    const sseText = `event: tool_call
data: {"tool":"web_search","timestamp":"2024-01-15T10:30:05Z"}`;

    const result = parseSSELine(sseText);

    expect(result).not.toBeNull();
    expect(result?.type).toBe('tool_call');
    expect(result?.data.tool).toBe('web_search');
  });

  it('handles tool_result event with result field', () => {
    const sseText = `event: tool_result
data: {"tool":"web_search","result":{"status":"success","data":"..."},"timestamp":"2024-01-15T10:30:10Z"}`;

    const result = parseSSELine(sseText);

    expect(result).not.toBeNull();
    expect(result?.type).toBe('tool_result');
    expect(result?.data.result).toEqual({ status: 'success', data: '...' });
  });

  it('returns null for empty input', () => {
    expect(parseSSELine('')).toBeNull();
    expect(parseSSELine('   ')).toBeNull();
    expect(parseSSELine('\n\n')).toBeNull();
  });

  it('returns null for event without type', () => {
    const sseText = `id: abc123
data: {"content":"No event type"}`;

    expect(parseSSELine(sseText)).toBeNull();
  });

  it('returns null for invalid JSON data', () => {
    const sseText = `event: thought
data: {invalid json}`;

    expect(parseSSELine(sseText)).toBeNull();
  });

  it('handles empty data field', () => {
    const sseText = `event: heartbeat
data: {}`;

    const result = parseSSELine(sseText);

    expect(result).not.toBeNull();
    expect(result?.type).toBe('heartbeat');
    expect(result?.data).toEqual({});
  });

  it('handles event with no data line', () => {
    const sseText = `event: done`;

    const result = parseSSELine(sseText);

    expect(result).not.toBeNull();
    expect(result?.type).toBe('done');
    expect(result?.data).toEqual({});
  });
});

describe('parseSSEStream', () => {
  it('parses multiple events separated by double newline', () => {
    const streamText = `event: thought
data: {"content":"First thought","timestamp":"2024-01-15T10:30:00Z"}

event: tool_call
data: {"tool":"search","timestamp":"2024-01-15T10:30:05Z"}

event: message
data: {"content":"Final answer","timestamp":"2024-01-15T10:31:00Z"}`;

    const results = parseSSEStream(streamText);

    expect(results).toHaveLength(3);
    expect(results[0].type).toBe('thought');
    expect(results[1].type).toBe('tool_call');
    expect(results[2].type).toBe('message');
  });

  it('handles events with ids', () => {
    const streamText = `id: event-1
event: thought
data: {"content":"Thought 1","timestamp":"2024-01-15T10:30:00Z"}

id: event-2
event: message
data: {"content":"Final","timestamp":"2024-01-15T10:31:00Z"}`;

    const results = parseSSEStream(streamText);

    expect(results).toHaveLength(2);
    expect(results[0].id).toBe('event-1');
    expect(results[1].id).toBe('event-2');
  });

  it('returns empty array for empty input', () => {
    expect(parseSSEStream('')).toEqual([]);
    expect(parseSSEStream('\n\n\n\n')).toEqual([]);
  });

  it('skips invalid events in stream', () => {
    const streamText = `event: thought
data: {"content":"Valid","timestamp":"2024-01-15T10:30:00Z"}

event: invalid-event
data: {bad json}

event: message
data: {"content":"Also valid","timestamp":"2024-01-15T10:31:00Z"}`;

    const results = parseSSEStream(streamText);

    expect(results).toHaveLength(2);
    expect(results[0].type).toBe('thought');
    expect(results[1].type).toBe('message');
  });
});

describe('validateEventContract', () => {
  it('validates thought event with required fields', () => {
    const event: ParsedSSEEvent = {
      type: 'thought',
      data: {
        content: 'Thinking...',
        timestamp: '2024-01-15T10:30:00Z',
      },
      raw: '',
    };

    expect(validateEventContract(event)).toBe(true);
  });

  it('throws ContractViolationError for missing content in thought', () => {
    const event: ParsedSSEEvent = {
      type: 'thought',
      data: {
        timestamp: '2024-01-15T10:30:00Z',
      },
      raw: '',
    };

    expect(() => validateEventContract(event)).toThrow(ContractViolationError);
    expect(() => validateEventContract(event)).toThrow('missing required fields [content]');
  });

  it('validates tool_call event with required fields', () => {
    const event: ParsedSSEEvent = {
      type: 'tool_call',
      data: {
        tool: 'web_search',
        timestamp: '2024-01-15T10:30:05Z',
      },
      raw: '',
    };

    expect(validateEventContract(event)).toBe(true);
  });

  it('throws for missing tool in tool_call', () => {
    const event: ParsedSSEEvent = {
      type: 'tool_call',
      data: {
        timestamp: '2024-01-15T10:30:05Z',
      },
      raw: '',
    };

    expect(() => validateEventContract(event)).toThrow('missing required fields [tool]');
  });

  it('validates tool_result event with required fields', () => {
    const event: ParsedSSEEvent = {
      type: 'tool_result',
      data: {
        tool: 'web_search',
        result: { status: 'success' },
        timestamp: '2024-01-15T10:30:10Z',
      },
      raw: '',
    };

    expect(validateEventContract(event)).toBe(true);
  });

  it('validates done event with only timestamp', () => {
    const event: ParsedSSEEvent = {
      type: 'done',
      data: {
        timestamp: '2024-01-15T10:31:00Z',
      },
      raw: '',
    };

    expect(validateEventContract(event)).toBe(true);
  });

  it('validates error event with required fields', () => {
    const event: ParsedSSEEvent = {
      type: 'error',
      data: {
        error: 'Something went wrong',
        timestamp: '2024-01-15T10:31:00Z',
      },
      raw: '',
    };

    expect(validateEventContract(event)).toBe(true);
  });

  it('returns true for event type with no contract (heartbeat)', () => {
    const event: ParsedSSEEvent = {
      type: 'heartbeat',
      data: {},
      raw: '',
    };

    expect(validateEventContract(event)).toBe(true);
  });

  it('validates expected type when provided', () => {
    const event: ParsedSSEEvent = {
      type: 'thought',
      data: { content: 'x', timestamp: 'x' },
      raw: '',
    };

    expect(validateEventContract(event, 'thought')).toBe(true);
  });

  it('throws when type does not match expected', () => {
    const event: ParsedSSEEvent = {
      type: 'thought',
      data: { content: 'x', timestamp: 'x' },
      raw: '',
    };

    expect(() => validateEventContract(event, 'message')).toThrow('expected type \'message\'');
  });
});

describe('createSSEParser', () => {
  it('processes chunks and emits events', () => {
    const onEvent = vi.fn();
    const onError = vi.fn();

    const parser = createSSEParser({ onEvent, onError });

    parser.processChunk(`event: thought
data: {"content":"Thinking...","timestamp":"2024-01-15T10:30:00Z"}

`);

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent.mock.calls[0][0].type).toBe('thought');
  });

  it('handles incremental parsing with buffer', () => {
    const onEvent = vi.fn();
    const onError = vi.fn();

    const parser = createSSEParser({ onEvent, onError });

    // First chunk (no complete event yet)
    parser.processChunk(`event: thought
data: {"content":"Th`);

    expect(onEvent).not.toHaveBeenCalled();

    // Second chunk (completes the event)
    parser.processChunk(`inking...","timestamp":"2024-01-15T10:30:00Z"}

`);

    expect(onEvent).toHaveBeenCalledTimes(1);
  });

  it('calls onContractViolation when contract fails', () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const onContractViolation = vi.fn();

    const parser = createSSEParser({
      onEvent,
      onError,
      onContractViolation,
      validateContracts: true,
    });

    // Event missing required 'content' field
    parser.processChunk(`event: thought
data: {"timestamp":"2024-01-15T10:30:00Z"}

`);

    expect(onContractViolation).toHaveBeenCalledTimes(1);
    expect(onContractViolation.mock.calls[0][0]).toBeInstanceOf(ContractViolationError);
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('skips contract validation when disabled', () => {
    const onEvent = vi.fn();
    const onError = vi.fn();

    const parser = createSSEParser({
      onEvent,
      onError,
      validateContracts: false,
    });

    // Event missing required 'content' field
    parser.processChunk(`event: thought
data: {"timestamp":"2024-01-15T10:30:00Z"}

`);

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it('flushes remaining buffer on flush call', () => {
    const onEvent = vi.fn();
    const onError = vi.fn();

    const parser = createSSEParser({ onEvent, onError });

    parser.processChunk(`event: thought
data: {"content":"Thinking...","timestamp":"2024-01-15T10:30:00Z"}`);

    expect(onEvent).not.toHaveBeenCalled();

    parser.flush();

    expect(onEvent).toHaveBeenCalledTimes(1);
  });

  it('reset clears buffer', () => {
    const onEvent = vi.fn();
    const onError = vi.fn();

    const parser = createSSEParser({ onEvent, onError });

    parser.processChunk(`event: thought
data: {"content":"Partial`);

    parser.reset();

    parser.flush();

    expect(onEvent).not.toHaveBeenCalled();
  });
});

describe('toSSEEvent', () => {
  it('converts parsed event to SSEEvent format', () => {
    const parsed: ParsedSSEEvent = {
      id: 'abc123',
      type: 'thought',
      data: {
        content: 'Thinking...',
        timestamp: '2024-01-15T10:30:00Z',
      },
      raw: '',
    };

    const sseEvent = toSSEEvent(parsed);

    expect(sseEvent.type).toBe('thought');
    expect(sseEvent.content).toEqual(parsed.data);
    expect(sseEvent.timestamp).toBe('2024-01-15T10:30:00Z');
    expect(sseEvent.event).toBe('thought');
    expect(sseEvent.data).toEqual(parsed.data);
  });

  it('handles tool_call with tool field', () => {
    const parsed: ParsedSSEEvent = {
      type: 'tool_call',
      data: {
        tool: 'web_search',
        timestamp: '2024-01-15T10:30:05Z',
      },
      raw: '',
    };

    const sseEvent = toSSEEvent(parsed);

    expect(sseEvent.tool).toBe('web_search');
  });

  it('handles tool_result with result field', () => {
    const parsed: ParsedSSEEvent = {
      type: 'tool_result',
      data: {
        tool: 'web_search',
        result: { status: 'success' },
        timestamp: '2024-01-15T10:30:10Z',
      },
      raw: '',
    };

    const sseEvent = toSSEEvent(parsed);

    expect(sseEvent.result).toEqual({ status: 'success' });
  });
});

describe('LastEventIdTracker', () => {
  it('tracks last event id', () => {
    const tracker = new LastEventIdTracker();

    const event1: ParsedSSEEvent = {
      id: 'event-1',
      type: 'thought',
      data: {},
      raw: '',
    };

    tracker.update(event1);

    expect(tracker.get()).toBe('event-1');

    const event2: ParsedSSEEvent = {
      id: 'event-2',
      type: 'message',
      data: {},
      raw: '',
    };

    tracker.update(event2);

    expect(tracker.get()).toBe('event-2');
  });

  it('does not update when event has no id', () => {
    const tracker = new LastEventIdTracker();

    const event: ParsedSSEEvent = {
      type: 'thought',
      data: {},
      raw: '',
    };

    tracker.update(event);

    expect(tracker.get()).toBeNull();
  });

  it('returns headers for resumption', () => {
    const tracker = new LastEventIdTracker();

    expect(tracker.getHeaders()).toEqual({});

    tracker.update({ id: 'event-123', type: 'thought', data: {}, raw: '' });

    expect(tracker.getHeaders()).toEqual({ 'Last-Event-ID': 'event-123' });
  });

  it('clears stored id', () => {
    const tracker = new LastEventIdTracker();

    tracker.update({ id: 'event-123', type: 'thought', data: {}, raw: '' });

    tracker.clear();

    expect(tracker.get()).toBeNull();
    expect(tracker.getHeaders()).toEqual({});
  });
});

describe('ContractViolationError', () => {
  it('contains event type and missing fields', () => {
    const error = new ContractViolationError(
      'thought',
      ['content', 'timestamp'],
      { foo: 'bar' }
    );

    expect(error.eventType).toBe('thought');
    expect(error.missingFields).toEqual(['content', 'timestamp']);
    expect(error.payload).toEqual({ foo: 'bar' });
    expect(error.message).toContain('thought');
    expect(error.message).toContain('content, timestamp');
  });
});

describe('EVENT_CONTRACTS', () => {
  it('defines contracts for key event types', () => {
    expect(EVENT_CONTRACTS.thought).toBeDefined();
    expect(EVENT_CONTRACTS.tool_call).toBeDefined();
    expect(EVENT_CONTRACTS.tool_result).toBeDefined();
    expect(EVENT_CONTRACTS.message).toBeDefined();
    expect(EVENT_CONTRACTS.done).toBeDefined();
    expect(EVENT_CONTRACTS.error).toBeDefined();
  });

  it('defines routing_decision contract (P2)', () => {
    expect(EVENT_CONTRACTS.routing_decision).toEqual([
      'complexity',
      'reasoning',
      'method',
      'mode',
      'sequence',
      'timestamp',
      'session_id',
    ]);
  });

  it('defines thinking_status contract (P2)', () => {
    expect(EVENT_CONTRACTS.thinking_status).toEqual([
      'status',
      'summary',
      'sequence',
      'timestamp',
      'session_id',
    ]);
  });
});