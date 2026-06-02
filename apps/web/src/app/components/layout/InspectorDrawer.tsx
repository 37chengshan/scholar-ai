import * as DialogPrimitive from "@radix-ui/react-dialog";
import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface InspectorDrawerProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  /** Width in pixels for tablet mode. Default 360. */
  width?: number;
  /** When true, uses full-screen overlay instead of side drawer. */
  fullScreen?: boolean;
}

export function InspectorDrawer({
  open,
  onClose,
  children,
  width = 360,
  fullScreen = false,
}: InspectorDrawerProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <AnimatePresence>
        {open && (
          <DialogPrimitive.Portal forceMount>
            {/* Overlay */}
            <DialogPrimitive.Overlay asChild forceMount>
              <motion.div
                key="inspector-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px]"
              />
            </DialogPrimitive.Overlay>

            {/* Drawer panel -- uses Radix Content for focus trap + inert */}
            <DialogPrimitive.Content asChild forceMount>
              <motion.div
                key="inspector-panel"
                role="dialog"
                aria-modal="true"
                aria-label="Inspector"
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 30, stiffness: 300 }}
                className={cn(
                  "fixed z-50 top-0 right-0 h-full bg-surface-sunken/95 backdrop-blur-md border-l border-border/60 shadow-2xl overflow-hidden outline-none",
                  fullScreen ? "w-full" : "",
                )}
                style={fullScreen ? undefined : { width: `${width}px` }}
              >
                {/* Close button */}
                <DialogPrimitive.Close
                  aria-label="Close inspector"
                  className="absolute top-4 right-4 z-10 inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border/60 bg-background/80 text-foreground/60 transition-colors hover:border-primary/25 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <X className="h-4 w-4" />
                </DialogPrimitive.Close>

                <div className="h-full overflow-y-auto pt-14">
                  {children}
                </div>
              </motion.div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        )}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}
