import { useCallback } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { PanelRightOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { useBreakpoint, type Breakpoint } from "@/app/components/ui/use-mobile";
import { InspectorDrawer } from "./InspectorDrawer";

interface WorkspaceShellProps {
  sidebar?: React.ReactNode;
  main: React.ReactNode;
  inspector?: React.ReactNode;
  layoutId: string;
  /**
   * Called when the user wants to open the inspector on mobile/tablet.
   * The consumer should set its inspector-visible state to true in this callback.
   * On desktop this is unused (inspector is always in the PanelGroup).
   */
  onInspectorOpen?: () => void;
  /**
   * Called when the inspector drawer is closed on mobile/tablet.
   * The consumer should set its inspector-visible state to false in this callback.
   */
  onInspectorClose?: () => void;
}

const StyledResizeHandle = ({ id }: { id: string }) => (
  <PanelResizeHandle
    id={id}
    className="relative flex w-2 items-center justify-center outline-none hover:bg-transparent data-[resize-handle-active]:bg-transparent group cursor-col-resize z-20"
  >
    <div className="w-[1px] h-full bg-stone-200 transition-colors duration-200 ease-out group-hover:bg-orange-400 group-hover:w-[2px] group-hover:shadow-[0_0_8px_rgba(234,88,12,0.3)] data-[resize-handle-active]:bg-orange-500 data-[resize-handle-active]:w-[2px]" />
  </PanelResizeHandle>
);

/**
 * Returns a breakpoint-specific autoSaveId so desktop and mobile
 * panel sizes do not overwrite each other.
 */
function panelSaveId(layoutId: string, breakpoint: Breakpoint): string {
  return `scholar-layout-${layoutId}-${breakpoint}`;
}

export function WorkspaceShell({
  sidebar,
  main,
  inspector,
  layoutId,
  onInspectorOpen,
  onInspectorClose,
}: WorkspaceShellProps) {
  const breakpoint = useBreakpoint();

  const handleDrawerClose = useCallback(() => {
    onInspectorClose?.();
  }, [onInspectorClose]);

  // Mobile: single column, no PanelGroup
  if (breakpoint === "mobile") {
    return (
      <div className="h-full w-full bg-background text-foreground overflow-hidden">
        <div className="relative h-full">
          {main}
          {/* Floating inspector trigger on mobile */}
          {onInspectorOpen && !inspector && (
            <button
              type="button"
              onClick={onInspectorOpen}
              className="absolute bottom-4 right-4 z-30 inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/60 bg-background/90 text-foreground/70 shadow-lg backdrop-blur-md transition-colors hover:border-primary/25 hover:text-primary"
              aria-label="Open inspector"
            >
              <PanelRightOpen className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Inspector as full-screen overlay on mobile */}
        {inspector && (
          <InspectorDrawer
            open
            onClose={handleDrawerClose}
            fullScreen
          >
            {inspector}
          </InspectorDrawer>
        )}
      </div>
    );
  }

  // Tablet: two-column (sidebar + main), inspector as drawer
  if (breakpoint === "tablet") {
    return (
      <div className="h-full w-full bg-background text-foreground overflow-hidden">
        <PanelGroup
          direction="horizontal"
          autoSaveId={panelSaveId(layoutId, "tablet")}
          className="h-full"
        >
          {sidebar && (
            <>
              <Panel defaultSize={25} minSize={20} maxSize={35} collapsible className="bg-surface-sunken/80">
                {sidebar}
              </Panel>
              <StyledResizeHandle id={`${layoutId}-tablet-handle`} />
            </>
          )}
          <Panel defaultSize={sidebar ? 75 : 100} minSize={50} className="bg-surface shadow-sm ring-1 ring-border z-10 overflow-hidden relative">
            {main}
            {/* Floating inspector trigger on tablet */}
            {onInspectorOpen && !inspector && (
              <button
                type="button"
                onClick={onInspectorOpen}
                className="absolute bottom-4 right-4 z-30 inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/60 bg-background/90 text-foreground/70 shadow-lg backdrop-blur-md transition-colors hover:border-primary/25 hover:text-primary"
                aria-label="Open inspector"
              >
                <PanelRightOpen className="h-4 w-4" />
              </button>
            )}
          </Panel>
        </PanelGroup>

        {/* Inspector as side drawer on tablet */}
        {inspector && (
          <InspectorDrawer
            open
            onClose={handleDrawerClose}
            width={360}
          >
            {inspector}
          </InspectorDrawer>
        )}
      </div>
    );
  }

  // Desktop: three-column PanelGroup (default behavior)
  return (
    <PanelGroup
      direction="horizontal"
      autoSaveId={panelSaveId(layoutId, "desktop")}
      className="h-full w-full bg-background text-foreground"
    >
      {sidebar && (
        <>
          <Panel defaultSize={20} minSize={15} maxSize={30} collapsible className="bg-surface-sunken/80">
            {sidebar}
          </Panel>
          <StyledResizeHandle id={`${layoutId}-handle-1`} />
        </>
      )}
      <Panel defaultSize={sidebar && inspector ? 50 : 70} minSize={40} className="bg-surface shadow-sm ring-1 ring-border z-10 overflow-hidden relative">
        {main}
      </Panel>
      {inspector && (
        <>
          <StyledResizeHandle id={`${layoutId}-handle-2`} />
          <Panel defaultSize={30} minSize={20} className="bg-surface-sunken/80">
            {inspector}
          </Panel>
        </>
      )}
    </PanelGroup>
  );
}
