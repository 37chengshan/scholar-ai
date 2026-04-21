import { describe, expect, it } from 'vitest';
import { parseScopeFromQuery } from './chatScopeQuery';

describe('parseScopeFromQuery', () => {
  it('marks query as error when paperId and kbId coexist', () => {
    const scope = parseScopeFromQuery(new URLSearchParams('paperId=paper-1&kbId=kb-1'));

    expect(scope.type).toBe('error');
    expect(scope.errorMessage).toContain('cannot coexist');
  });
});