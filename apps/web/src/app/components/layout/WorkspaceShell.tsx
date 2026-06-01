import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { cn } from "@/lib/utils";

interface WorkspaceShellProps {
  sidebar?: React.ReactNode;
  main: React.ReactNode;
  inspector?: React.ReactNode;
  layoutId: string;
}

const StyledResizeHandle = ({ id }: { id: string }) => (
  // Enlarged hit box but visually centered line
  <PanelResizeHandle
    id={id}
    className="relative flex w-2 items-center justify-center outline-none hover:bg-transparent data-[resize-handle-active]:bg-transparent group cursor-col-resize z-20"
  >
    <div className="w-[1px] h-full bg-stone-200 transition-colors duration-200 ease-out group-hover:bg-orange-400 group-hover:w-[2px] group-hover:shadow-[0_0_8px_rgba(234,88,12,0.3)] data-[resize-handle-active]:bg-orange-500 data-[resize-handle-active]:w-[2px]" />
  </PanelResizeHandle>
);

export function WorkspaceShell({ sidebar, main, inspector, layoutId }: WorkspaceShellProps) {
  return (
    <PanelGroup direction="horizontal" autoSaveId={`scholar-layout-${layoutId}`} className="h-full w-full bg-background text-foreground">
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
