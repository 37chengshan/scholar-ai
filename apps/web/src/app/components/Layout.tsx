import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { BookOpen, Search, Settings, MessageSquare, LogOut, Menu } from "lucide-react";
import { useLanguage } from "../contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import { Logo } from "./landing/Logo";
import { Sheet, SheetContent } from "./ui/sheet";
import { useState } from "react";
import { WorkflowShell } from "@/features/workflow/components/WorkflowShell";
import { selectWorkflowSurfaceVisible } from "@/features/workflow/state/workflowSelectors";

const navItemsEN = [
  { to: "/chat", icon: MessageSquare, label: "Workspace" },
  { to: "/knowledge-bases", icon: BookOpen, label: "Library" },
  { to: "/search", icon: Search, label: "Search" },
];

const navItemsZH = [
  { to: "/chat", icon: MessageSquare, label: "工作台" },
  { to: "/knowledge-bases", icon: BookOpen, label: "资源库" },
  { to: "/search", icon: Search, label: "检索" },
];

export function Layout() {
  const { language } = useLanguage();
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isZh = language === "zh";
  const navItems = isZh ? navItemsZH : navItemsEN;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isChatRoute = location.pathname.startsWith('/chat');
  const showWorkflowShell = selectWorkflowSurfaceVisible(location.pathname);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };
  
  const handleNavClick = (to: string) => {
    navigate(to);
    setMobileMenuOpen(false);
  };

  return (
    <div className="h-screen bg-background text-foreground font-sans flex flex-col antialiased overflow-hidden">
      <header className="h-14 flex-shrink-0 border-b border-border/70 bg-paper-2/95 backdrop-blur-md z-40 flex items-center justify-between px-4 lg:px-6 relative shadow-sm">
        {/* Left Side: Logo & Main Navigation */}
        <div className="flex items-center gap-6 lg:gap-8 h-full">
          {/* Logo Area */}
          <Logo />

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="md:hidden p-2 rounded-sm hover:bg-muted transition-colors"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 lg:gap-2 pl-6 lg:pl-8 border-l border-border/60 h-8">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-sm flex items-center gap-2 transition-all duration-200 group ${
                    isActive
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "hover:bg-muted text-foreground/70 hover:text-primary"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon className={`w-3.5 h-3.5 ${isActive ? "text-primary-foreground" : "text-primary/70 group-hover:text-primary"}`} />
                    <span className="text-[10px] lg:text-[11px] font-semibold tracking-wide">{item.label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right Side: Settings & User Profile & Logout */}
        <div className="flex items-center gap-3 lg:gap-4 h-full">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `p-1.5 rounded-full transition-all duration-300 group border border-transparent ${
                isActive
                      ? "bg-muted text-primary border-border/60"
                      : "text-foreground/60 hover:bg-muted hover:text-primary hover:border-border/60"
              }`
            }
          >
            <Settings className="w-4 h-4" />
          </NavLink>

<div className="w-px h-6 bg-border/50 hidden lg:block" />

           <button
             onClick={() => navigate('/settings')}
             className="flex items-center gap-3 group rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
             aria-label={isZh ? '打开个人设置' : 'Open profile settings'}
           >
<div className="hidden lg:flex flex-col text-right justify-center">
               <span className="text-[9px] font-semibold tracking-widest text-primary leading-none mb-0.5">
                 {isZh ? "在线" : "Active"}
               </span>
               <span className="text-[12px] font-serif font-semibold text-foreground leading-none">
                 {user?.name || "用户"}
               </span>
             </div>
             <div className="w-7 h-7 rounded-full overflow-hidden border border-primary/20 p-0.5 shadow-sm group-hover:shadow-primary/20 transition-all duration-300">
               <img
                 src={user?.avatar || "/default-avatar.png"}
                 alt={user?.name || "User"}
                 className="w-full h-full rounded-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
               />
             </div>
          </button>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-full transition-all duration-300 text-foreground/60 hover:bg-muted hover:text-primary hover:border-border/50 border border-transparent flex items-center gap-2"
            title={isZh ? "退出登录" : "Logout"}
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Area — No noise texture on Chat route */}
      <main className="flex-1 flex flex-col min-h-0 bg-background relative">
        {showWorkflowShell ? <WorkflowShell /> : null}
        {!isChatRoute && (
          <svg className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none z-10 mix-blend-multiply">
            <filter id="noiseFilter">
              <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
            </filter>
            <rect width="100%" height="100%" filter="url(#noiseFilter)" />
          </svg>
        )}
        <div className={isChatRoute ? 'flex-1 overflow-hidden' : 'flex-1 overflow-y-auto z-10'}>
          <Outlet />
        </div>
      </main>

      {/* Mobile Navigation Sheet */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-[320px] p-0">
          <div className="flex flex-col h-full bg-paper-2">
            {/* Header */}
            <div className="p-4 border-b border-border/60 flex justify-between items-center">
              <Logo />
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-2 hover:bg-muted rounded-sm"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 overflow-y-auto py-4">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                      `flex items-center gap-3 px-6 py-3 text-sm font-semibold transition-colors ${
                      isActive
                          ? 'bg-primary text-primary-foreground'
                        : 'text-foreground hover:bg-muted'
                    }`
                  }
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </NavLink>
              ))}
            </nav>

{/* User Profile */}
             <div className="p-4 border-t border-border/60">
               <button
                 onClick={() => {
                   handleNavClick('/settings');
                 }}
                 className="flex w-full items-center gap-3 hover:bg-muted p-2 rounded-sm text-left"
                 aria-label={isZh ? '查看个人设置' : 'View profile settings'}
               >
                 <div className="w-8 h-8 rounded-full overflow-hidden border border-primary/20">
                   <img
                     src={user?.avatar || "/default-avatar.png"}
                     alt={user?.name || "User"}
                     className="w-full h-full object-cover"
                   />
                 </div>
                 <div className="flex-1">
                   <div className="text-sm font-semibold">
                     {user?.name || "用户"}
                   </div>
                   <div className="text-xs text-muted-foreground">
                     {isZh ? "查看个人设置" : "View Settings"}
                   </div>
                 </div>
               </button>
             </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
