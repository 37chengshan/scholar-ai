import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router";
import { Menu, Settings } from "lucide-react";
import { clsx } from "clsx";
import { useLanguage } from "../contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "./ui/sheet";
import { SidebarContent } from "./layout/SidebarContent";

const LEFT_SIDEBAR_STORAGE_KEY = "scholarai-left-sidebar-collapsed";

export function Layout() {
  const { language } = useLanguage();
  const { logout, user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const isZh = language === "zh";
  const locale = isZh ? "zh-CN" : "en-US";

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(LEFT_SIDEBAR_STORAGE_KEY);
      setLeftCollapsed(stored === "1");
    } catch {
      setLeftCollapsed(false);
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(LEFT_SIDEBAR_STORAGE_KEY, leftCollapsed ? "1" : "0");
    } catch {
      // Ignore storage failures.
    }
  }, [leftCollapsed]);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const sidebarProps = {
    isZh,
    locale,
    leftCollapsed,
    setLeftCollapsed,
    mobileMenuOpen,
    setMobileMenuOpen,
    isAuthenticated,
    userName: user?.name,
    userAvatar: user?.avatar,
    onLogout: handleLogout,
  };

  return (
    <div className="relative flex h-dvh overflow-hidden bg-background text-foreground antialiased">
      {/* Desktop sidebar */}
      <aside className={clsx(
        "hidden shrink-0 border-r-2 border-border/70 bg-gradient-to-b from-muted/40 to-background shadow-2xl transition-[width] duration-200 md:block",
        leftCollapsed ? "w-[var(--sidebar-collapsed)]" : "w-[var(--sidebar-expanded)]",
      )}>
        <SidebarContent {...sidebarProps} />
      </aside>

      {/* Main content area */}
      <div className="relative flex min-w-0 flex-1 overflow-hidden bg-background">
        {/* Mobile top bar */}
        <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between px-4 pt-4 md:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(true)}
            className="pointer-events-auto inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-border/60 bg-paper-1/90 text-foreground/72 backdrop-blur-md"
            aria-label={isZh ? "打开导航" : "Open navigation"}
          >
            <Menu className="h-4 w-4" />
          </button>
          <Link
            to="/settings"
            className="pointer-events-auto inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-border/60 bg-paper-1/90 text-foreground/72 backdrop-blur-md"
            aria-label={isZh ? "打开设置" : "Open settings"}
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>

        <main className="relative min-h-0 flex-1 overflow-hidden pt-16 md:pt-0">
          <Outlet />
        </main>
      </div>

      {/* Mobile sheet sidebar */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-[292px] border-r border-border/60 bg-paper-2 p-0">
          <SheetTitle className="sr-only">{isZh ? "移动导航菜单" : "Mobile navigation menu"}</SheetTitle>
          <SheetDescription className="sr-only">
            {isZh ? "打开工作区导航、最近会话、知识库和账号操作。" : "Open workspace navigation, recent threads, knowledge bases, and account actions."}
          </SheetDescription>
          <SidebarContent {...sidebarProps} />
        </SheetContent>
      </Sheet>
    </div>
  );
}
