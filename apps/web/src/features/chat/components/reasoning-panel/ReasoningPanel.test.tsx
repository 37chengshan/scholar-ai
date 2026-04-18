import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ReasoningPanel } from './ReasoningPanel';

describe('ReasoningPanel', () => {
  it('renders thinking content when visible', () => {
    render(
      <ReasoningPanel
        visible={true}
        steps={[{ type: 'thinking', content: 'step-1' }]}
        durationSeconds={1.2}
      />
    );

    expect(screen.getByText('step-1')).toBeInTheDocument();
  });

  it('renders nothing when hidden', () => {
    const { container } = render(
      <ReasoningPanel visible={false} steps={[{ type: 'thinking', content: 'step-1' }]} durationSeconds={1.2} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
