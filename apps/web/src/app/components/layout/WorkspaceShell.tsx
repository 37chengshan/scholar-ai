import { useEffect, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

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
  const [isCompactLayout, setIsCompactLayout] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.matchMedia("(max-width: 767px)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const onChange = (event: MediaQueryListEvent) => setIsCompactLayout(event.matches);

    setIsCompactLayout(mediaQuery.matches);
    mediaQuery.addEventListener("change", onChange);

    return () => {
      mediaQuery.removeEventListener("change", onChange);
    };
  }, []);

  if (isCompactLayout) {
    return (
      <div className="flex h-full w-full flex-col overflow-y-auto bg-stone-50 text-stone-900">
        <div className="min-h-[50vh] flex-none bg-white shadow-sm ring-1 ring-stone-900/5">
          {main}
        </div>
        {sidebar && (
          <div className="flex-none border-t border-stone-200 bg-stone-50/80">
            {sidebar}
          </div>
        )}
        {inspector && (
          <div className="flex-none border-t border-stone-200 bg-stone-50/80">
            {inspector}
          </div>
        )}
      </div>
    );
  }

  return (
    <PanelGroup direction="horizontal" autoSaveId={`scholar-layout-${layoutId}`} className="h-full w-full bg-stone-50 text-stone-900">
      {sidebar && (
        <>
          <Panel defaultSize={20} minSize={15} maxSize={30} collapsible className="bg-stone-50/80">
            {sidebar}
          </Panel>
          <StyledResizeHandle id={`${layoutId}-handle-1`} />
        </>
      )}
      <Panel defaultSize={sidebar && inspector ? 50 : 70} minSize={40} className="bg-white shadow-sm ring-1 ring-stone-900/5 z-10 overflow-hidden relative">
        {main}
      </Panel>
      {inspector && (
        <>
          <StyledResizeHandle id={`${layoutId}-handle-2`} />
          <Panel defaultSize={30} minSize={20} className="bg-stone-50/80">
            {inspector}
          </Panel>
        </>
      )}
    </PanelGroup>
  );
}
