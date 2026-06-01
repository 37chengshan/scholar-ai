import * as React from "react";

export const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
} as const;

export type Breakpoint = "mobile" | "tablet" | "desktop";

export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = React.useState<Breakpoint>("desktop");

  React.useEffect(() => {
    const mobileMql = window.matchMedia(`(max-width: ${BREAKPOINTS.mobile - 1}px)`);
    const tabletMql = window.matchMedia(`(max-width: ${BREAKPOINTS.tablet - 1}px)`);

    const update = () => {
      if (mobileMql.matches) {
        setBreakpoint("mobile");
      } else if (tabletMql.matches) {
        setBreakpoint("tablet");
      } else {
        setBreakpoint("desktop");
      }
    };

    update();
    mobileMql.addEventListener("change", update);
    tabletMql.addEventListener("change", update);

    return () => {
      mobileMql.removeEventListener("change", update);
      tabletMql.removeEventListener("change", update);
    };
  }, []);

  return breakpoint;
}

/** @deprecated Use `useBreakpoint() === 'mobile'` instead. Kept for backward compatibility. */
export function useIsMobile() {
  const breakpoint = useBreakpoint();
  return breakpoint === "mobile";
}
