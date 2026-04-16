/**
 * SSE Event Types Tests
 *
 * Tests for SSE event type definitions:
 * - Type completeness validation
 * - Contract field verification
 * - Type guard correctness
 * - Helper function validation
 */

import { describe, it, expect } from 'vitest';
import {
  SSEEventType,
  ThinkingStatus,
  SSEEvent,
  RoutingDecisionData,
  ThinkingStatusData,
  StepProgressData,
  ThoughtData,
  ToolCallData,
  ToolResultData,
  MessageData,
  ErrorData,
  DoneData,
  isSSEEventOfType,
  createSSEEvent,
} from '../sse';

describe('SSEEventType enum', () => {
  it('should contain all required event types', () => {
    // New event types (HARD RULE 0.2)
    const newEventTypes = [
      'session_start',
      'routing_decision',
      'phase',
      'reasoning',
      'message',
      'tool_call',
      'tool_result',
      'citation',
      'confirmation_required',
      'cancel',
      'done',
      'error',
      'heartbeat',
    ];

    // Legacy event types (backward compatibility)
    const legacyEventTypes = [
      'thinking_status',
      'step_progress',
      'thought',
    ];

    const expectedTypes = [...newEventTypes, ...legacyEventTypes];

    const actualTypes = Object.values(SSEEventType);

    // Check all new event types are present
    newEventTypes.forEach((type) => {
      expect(actualTypes).toContain(type);
    });
  });

  it('should have correct enum values', () => {
    // New event types (HARD RULE 0.2)
    expect(SSEEventType.SESSION_START).toBe('session_start');
    expect(SSEEventType.ROUTING_DECISION).toBe('routing_decision');
    expect(SSEEventType.PHASE).toBe('phase');
    expect(SSEEventType.REASONING).toBe('reasoning');
    expect(SSEEventType.TOOL_CALL).toBe('tool_call');
    expect(SSEEventType.TOOL_RESULT).toBe('tool_result');
    expect(SSEEventType.MESSAGE).toBe('message');
    expect(SSEEventType.CITATION).toBe('citation');
    expect(SSEEventType.CONFIRMATION_REQUIRED).toBe('confirmation_required');
    expect(SSEEventType.CANCEL).toBe('cancel');
    expect(SSEEventType.ERROR).toBe('error');
    expect(SSEEventType.DONE).toBe('done');
    expect(SSEEventType.HEARTBEAT).toBe('heartbeat');
    // Legacy event types
    expect(SSEEventType.THINKING_STATUS).toBe('thinking_status');
    expect(SSEEventType.STEP_PROGRESS).toBe('step_progress');
    expect(SSEEventType.THOUGHT).toBe('thought');
  });
});

describe('ThinkingStatus enum', () => {
  it('should contain all required statuses', () => {
    const expectedStatuses = [
      'idle',
      'analyzing',
      'retrieving',
      'reading',
      'tool_calling',
      'synthesizing',
      'verifying',
      'done',
      'error',
      'cancelled',
    ];

    const actualStatuses = Object.values(ThinkingStatus);

    expectedStatuses.forEach((status) => {
      expect(actualStatuses).toContain(status);
    });
  });

  it('should have correct enum values', () => {
    expect(ThinkingStatus.IDLE).toBe('idle');
    expect(ThinkingStatus.ANALYZING).toBe('analyzing');
    expect(ThinkingStatus.PLANNING).toBe('tool_calling'); // Legacy alias
    expect(ThinkingStatus.EXECUTING).toBe('retrieving'); // Legacy alias
    expect(ThinkingStatus.SYNTHESIZING).toBe('synthesizing');
    expect(ThinkingStatus.TOOL_CALLING).toBe('tool_calling');
    expect(ThinkingStatus.RETRIEVING).toBe('retrieving');
    expect(ThinkingStatus.READING).toBe('reading');
    expect(ThinkingStatus.VERIFYING).toBe('verifying');
    expect(ThinkingStatus.DONE).toBe('done');
    expect(ThinkingStatus.ERROR).toBe('error');
    expect(ThinkingStatus.CANCELLED).toBe('cancelled');
  });
});

describe('SSEEvent contract fields', () => {
  it('should require id field (UUID)', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(event.id).toBeDefined();
    expect(typeof event.id).toBe('string');
  });

  it('should require sequence field (number)', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(event.sequence).toBeDefined();
    expect(typeof event.sequence).toBe('number');
  });

  it('should require timestamp field (number)', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(event.timestamp).toBeDefined();
    expect(typeof event.timestamp).toBe('number');
  });

  it('should require session_id field (string)', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(event.session_id).toBeDefined();
    expect(typeof event.session_id).toBe('string');
  });

  // HARD RULE 0.2: message_id is required
  it('should require message_id field (string)', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123',
    };

    expect(event.message_id).toBeDefined();
    expect(typeof event.message_id).toBe('string');
  });

  it('should require type field (SSEEventType)', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(event.type).toBeDefined();
    expect(Object.values(SSEEventType)).toContain(event.type);
  });

  it('should require data field', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: {},
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(event.data).toBeDefined();
  });
});

describe('Event data interfaces', () => {
  it('RoutingDecisionData should have required fields', () => {
    const data: RoutingDecisionData = {
      route: 'rag',
      confidence: 0.95,
      reason: 'Query matches local knowledge base',
    };

    expect(data.route).toBeDefined();
    expect(data.confidence).toBeGreaterThanOrEqual(0);
    expect(data.confidence).toBeLessThanOrEqual(1);
    expect(data.reason).toBeDefined();
  });

  it('ThinkingStatusData should have required fields', () => {
    const data: ThinkingStatusData = {
      status: ThinkingStatus.ANALYZING,
    };

    expect(data.status).toBeDefined();
    expect(Object.values(ThinkingStatus)).toContain(data.status);
  });

  it('StepProgressData should have required fields', () => {
    const data: StepProgressData = {
      step_id: 'step-1',
      step_name: 'rag_search',
      status: 'completed',
    };

    expect(data.step_id).toBeDefined();
    expect(data.step_name).toBeDefined();
    expect(['started', 'in_progress', 'completed', 'failed']).toContain(data.status);
  });

  it('ThoughtData should have required fields', () => {
    const data: ThoughtData = {
      content: 'Analyzing query structure...',
    };

    expect(data.content).toBeDefined();
    expect(typeof data.content).toBe('string');
  });

  it('ToolCallData should have required fields', () => {
    const data: ToolCallData = {
      tool_call_id: 'tc-1',
      tool_name: 'rag_search',
      parameters: { query: 'test' },
    };

    expect(data.tool_call_id).toBeDefined();
    expect(data.tool_name).toBeDefined();
    expect(data.parameters).toBeDefined();
  });

  it('ToolResultData should have required fields', () => {
    const data: ToolResultData = {
      tool_call_id: 'tc-1',
      tool_name: 'rag_search',
      status: 'success',
      duration: 500,
    };

    expect(data.tool_call_id).toBeDefined();
    expect(data.tool_name).toBeDefined();
    expect(['success', 'error', 'timeout']).toContain(data.status);
    expect(data.duration).toBeDefined();
  });

  it('MessageData should have required fields', () => {
    const data: MessageData = {
      content: 'Response content here',
    };

    expect(data.content).toBeDefined();
    expect(typeof data.content).toBe('string');
  });

  it('ErrorData should have required fields', () => {
    const data: ErrorData = {
      code: 'RATE_LIMIT',
      message: 'Rate limit exceeded',
      severity: 'warning',
    };

    expect(data.code).toBeDefined();
    expect(data.message).toBeDefined();
    expect(['warning', 'error', 'critical']).toContain(data.severity);
  });

  it('DoneData should have optional fields', () => {
    const data: DoneData = {
      finish_reason: 'stop',
    };

    expect(data.finish_reason).toBeDefined();
    expect(['stop', 'tool_calls', 'length', 'cancel']).toContain(data.finish_reason);
  });
});

describe('isSSEEventOfType type guard', () => {
  it('should return true for matching event type', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: { content: 'test' },
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(isSSEEventOfType(event, SSEEventType.MESSAGE)).toBe(true);
  });

  it('should return false for non-matching event type', () => {
    const event: SSEEvent = {
      id: 'uuid-123',
      sequence: 1,
      timestamp: Date.now(),
      session_id: 'session-abc',
      type: SSEEventType.MESSAGE,
      data: { content: 'test' },
      message_id: 'msg-123', // HARD RULE 0.2
    };

    expect(isSSEEventOfType(event, SSEEventType.ERROR)).toBe(false);
  });

  it('should work for all event types', () => {
    const eventTypes = Object.values(SSEEventType);

    eventTypes.forEach((eventType) => {
      const event: SSEEvent = {
        id: 'uuid-123',
        sequence: 1,
        timestamp: Date.now(),
        session_id: 'session-abc',
        type: eventType,
        data: {},
        message_id: 'msg-123', // HARD RULE 0.2
      };

      expect(isSSEEventOfType(event, eventType)).toBe(true);
    });
  });
});

describe('createSSEEvent helper', () => {
  it('should create event with all contract fields including message_id (HARD RULE 0.2)', () => {
    const event = createSSEEvent(
      SSEEventType.MESSAGE,
      { content: 'test' },
      'session-abc',
      1,
      'msg-123' // message_id
    );

    expect(event.id).toBeDefined();
    expect(event.sequence).toBe(1);
    expect(event.timestamp).toBeDefined();
    expect(event.session_id).toBe('session-abc');
    expect(event.type).toBe(SSEEventType.MESSAGE);
    expect(event.data).toEqual({ content: 'test' });
    expect(event.message_id).toBe('msg-123'); // HARD RULE 0.2
  });

  it('should generate valid UUID for id', () => {
    const event = createSSEEvent(
      SSEEventType.MESSAGE,
      {},
      'session-abc',
      1
    );

    // UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
    expect(event.id).toMatch(uuidRegex);
  });

  it('should generate message_id if not provided (HARD RULE 0.2)', () => {
    const event = createSSEEvent(
      SSEEventType.MESSAGE,
      {},
      'session-abc',
      1
    );

    expect(event.message_id).toBeDefined();
    expect(typeof event.message_id).toBe('string');
  });

  it('should increment sequence correctly', () => {
    const event1 = createSSEEvent(SSEEventType.MESSAGE, {}, 'session-abc', 1);
    const event2 = createSSEEvent(SSEEventType.MESSAGE, {}, 'session-abc', 2);

    expect(event1.sequence).toBe(1);
    expect(event2.sequence).toBe(2);
  });

  it('should set current timestamp', () => {
    const before = Date.now();
    const event = createSSEEvent(SSEEventType.MESSAGE, {}, 'session-abc', 1);
    const after = Date.now();

    expect(event.timestamp).toBeGreaterThanOrEqual(before);
    expect(event.timestamp).toBeLessThanOrEqual(after);
  });

  it('should preserve data payload', () => {
    const routingData: RoutingDecisionData = {
      route: 'hybrid',
      confidence: 0.8,
      reason: 'Complex query requires multiple sources',
    };

    const event = createSSEEvent(
      SSEEventType.ROUTING_DECISION,
      routingData,
      'session-abc',
      1
    );

    expect(event.data.route).toBe('hybrid');
    expect(event.data.confidence).toBe(0.8);
    expect(event.data.reason).toBe('Complex query requires multiple sources');
  });
});