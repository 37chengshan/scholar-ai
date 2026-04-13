import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StepTimeline } from '../StepTimeline';

// Step type definition (inline for test)
interface Step {
  name: string;
  status: 'pending' | 'running' | 'success' | 'error';
  duration?: number;
  thought?: string;
}

describe('StepTimeline', () => {
  const defaultSteps: Step[] = [
    { name: 'Initialize', status: 'pending' },
    { name: 'Analyze query', status: 'pending' },
    { name: 'Search papers', status: 'pending' },
  ];

  it('renders all step names', () => {
    render(<StepTimeline steps={defaultSteps} />);
    expect(screen.getByText('Initialize')).toBeInTheDocument();
    expect(screen.getByText('Analyze query')).toBeInTheDocument();
    expect(screen.getByText('Search papers')).toBeInTheDocument();
  });

  it('displays correct icons for each status type', () => {
    const steps: Step[] = [
      { name: 'Pending step', status: 'pending' },
      { name: 'Running step', status: 'running' },
      { name: 'Success step', status: 'success' },
      { name: 'Error step', status: 'error' },
    ];
    render(<StepTimeline steps={steps} />);

    // Each status icon should be present
    const statusIcons = screen.getAllByRole('status');
    expect(statusIcons).toHaveLength(4);
  });

  it('displays duration for completed steps', () => {
    const steps: Step[] = [
      { name: 'Completed step', status: 'success', duration: 2500 },
      { name: 'Running step', status: 'running', duration: 1500 },
    ];
    render(<StepTimeline steps={steps} />);

    // Duration should be formatted
    expect(screen.getByText(/2\.5s/)).toBeInTheDocument();
    expect(screen.getByText(/1\.5s/)).toBeInTheDocument();
  });

  it('displays thought preview when provided', () => {
    const steps: Step[] = [
      {
        name: 'Planning step',
        status: 'running',
        thought: 'Analyzing the user query to determine the best search strategy...',
      },
    ];
    render(<StepTimeline steps={steps} />);

    // Thought preview should be displayed (truncated)
    expect(screen.getByText(/Analyzing the user query/)).toBeInTheDocument();
  });

  it('truncates long thought preview', () => {
    const longThought =
      'This is a very long thought that should be truncated because it exceeds the maximum display length and we want to keep the UI clean and readable for users.';
    const steps: Step[] = [
      { name: 'Long thought step', status: 'running', thought: longThought },
    ];
    render(<StepTimeline steps={steps} />);

    // Should not show full text, but truncated version
    const thoughtEl = screen.getByText(/This is a very long thought/);
    expect(thoughtEl.textContent?.length).toBeLessThan(longThought.length);
  });

  it('applies running animation to current running step', () => {
    const steps: Step[] = [
      { name: 'Completed', status: 'success' },
      { name: 'Running step', status: 'running' },
      { name: 'Pending', status: 'pending' },
    ];
    render(<StepTimeline steps={steps} />);

    // Find the timeline container and get the running step (index 1)
    const timeline = screen.getByTestId('step-timeline');
    const stepContainers = timeline.querySelectorAll(':scope > div');
    const runningStepContainer = stepContainers[1];

    // Running step should have animation class
    expect(runningStepContainer.className).toMatch(/animate|pulse|running/);
  });

  it('applies success styling to completed steps', () => {
    const steps: Step[] = [
      { name: 'Success step', status: 'success' },
    ];
    render(<StepTimeline steps={steps} />);

    const statusEl = screen.getByRole('status');
    expect(statusEl.className).toMatch(/green|success|completed/);
  });

  it('applies error styling to failed steps', () => {
    const steps: Step[] = [
      { name: 'Error step', status: 'error' },
    ];
    render(<StepTimeline steps={steps} />);

    const statusEl = screen.getByRole('status');
    expect(statusEl.className).toMatch(/red|error|failed/);
  });

  it('applies pending styling to waiting steps', () => {
    const steps: Step[] = [
      { name: 'Pending step', status: 'pending' },
    ];
    render(<StepTimeline steps={steps} />);

    const statusEl = screen.getByRole('status');
    expect(statusEl.className).toMatch(/gray|pending|muted/);
  });

  it('renders empty state when no steps provided', () => {
    render(<StepTimeline steps={[]} />);
    // Should render without crashing, possibly with empty message or nothing
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('highlights current step when currentStep index provided', () => {
    const steps: Step[] = [
      { name: 'Step 1', status: 'success' },
      { name: 'Step 2', status: 'running' },
      { name: 'Step 3', status: 'pending' },
    ];
    render(<StepTimeline steps={steps} currentStep={1} />);

    // Find the timeline container and get the current step (index 1)
    const timeline = screen.getByTestId('step-timeline');
    const stepContainers = timeline.querySelectorAll(':scope > div');
    const currentStepContainer = stepContainers[1];

    // Current step should be highlighted
    expect(currentStepContainer.className).toMatch(/current|active|highlight|muted\/40/);
  });

  it('formats duration correctly for different values', () => {
    const steps: Step[] = [
      { name: 'Short', status: 'success', duration: 500 },
      { name: 'Medium', status: 'success', duration: 45000 },
      { name: 'Long', status: 'success', duration: 125000 },
    ];
    render(<StepTimeline steps={steps} />);

    expect(screen.getByText(/0\.5s/)).toBeInTheDocument();
    expect(screen.getByText(/45\.0s|45s/)).toBeInTheDocument();
    expect(screen.getByText(/2m 5s|125\.0s/)).toBeInTheDocument();
  });

  it('renders steps in vertical timeline layout', () => {
    const steps: Step[] = [
      { name: 'Step 1', status: 'success' },
      { name: 'Step 2', status: 'running' },
      { name: 'Step 3', status: 'pending' },
    ];
    render(<StepTimeline steps={steps} />);

    // Timeline should have vertical layout class
    const timeline = screen.getByTestId('step-timeline');
    expect(timeline.className).toMatch(/flex-col|vertical|timeline/);
  });
});