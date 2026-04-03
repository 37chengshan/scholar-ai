import { NavLink, Outlet } from "react-router";
import { clsx } from "clsx";
import { BookOpen, Search, Settings, MessageSquare, LayoutDashboard, FileText, UploadCloud } from "lucide-react";
import { useLanguage } from "../contexts/LanguageContext";

const navItemsEN = [
  { to: "/", icon: LayoutDashboard, label: "Overview" },
  { to: "/upload", icon: UploadCloud, label: "Ingest" },
  { to: "/library", icon: BookOpen, label: "Literature" },
  { to: "/search", icon: Search, label: "Discovery" },
  { to: "/read", icon: FileText, label: "Reading" },
  { to: "/chat", icon: MessageSquare, label: "Terminal" },
];

const navItemsZH = [
  { to: "/", icon: LayoutDashboard, label: "仪表盘" },
  { to: "/upload", icon: UploadCloud, label: "上传/导入" },
  { to: "/library", icon: BookOpen, label: "文献库" },
  { to: "/search", icon: Search, label: "检索" },
  { to: "/read", icon: FileText, label: "阅读" },
  { to: "/chat", icon: MessageSquare, label: "终端对话" },
];

export function Layout() {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const navItems = isZh ? navItemsZH : navItemsEN;

  return (
    <div className="h-screen bg-background text-foreground font-sans flex flex-col antialiased overflow-hidden">
      {/* Top Navbar: Ultra-compact, high-density header */}
      <header className="h-14 flex-shrink-0 border-b border-border/50 bg-background/90 backdrop-blur-md z-40 flex items-center justify-between px-4 lg:px-6 relative shadow-sm">
        {/* Left Side: Logo & Main Navigation */}
        <div className="flex items-center gap-6 lg:gap-8 h-full">
          {/* Logo Area */}
          <div className="flex items-baseline gap-2">
            <h1 className="font-serif text-lg lg:text-xl font-black tracking-tighter leading-none text-foreground">
              ScholarAI
            </h1>
            <div className="text-[8px] font-bold tracking-[0.3em] uppercase text-primary hidden sm:block">Vol.4</div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 lg:gap-2 pl-6 lg:pl-8 border-l border-border/50 h-8">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    "px-3 py-1.5 rounded-full flex items-center gap-2 transition-all duration-300 group",
                    isActive 
                      ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" 
                      : "hover:bg-muted text-foreground/70 hover:text-primary"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon className={clsx("w-3.5 h-3.5", isActive ? "text-primary-foreground" : "text-primary/70 group-hover:text-primary")} />
                    <span className="text-[9px] lg:text-[10px] font-bold tracking-[0.2em] uppercase">{item.label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right Side: Settings & User Profile */}
        <div className="flex items-center gap-3 lg:gap-4 h-full">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              clsx(
                "p-1.5 rounded-full transition-all duration-300 group border border-transparent",
                isActive 
                  ? "bg-muted text-primary border-border/50" 
                  : "text-foreground/60 hover:bg-muted hover:text-primary hover:border-border/50"
              )
            }
          >
            <Settings className="w-4 h-4" />
          </NavLink>

          <div className="w-px h-6 bg-border/50 hidden lg:block" />

          <div className="flex items-center gap-3 cursor-pointer group">
            <div className="hidden lg:flex flex-col text-right justify-center">
              <span className="text-[8px] font-bold tracking-[0.3em] uppercase text-primary leading-none mb-0.5">
                {isZh ? "在线" : "Active"}
              </span>
              <span className="text-[11px] font-serif font-bold text-foreground leading-none">Dr. Vance</span>
            </div>
            <div className="w-7 h-7 rounded-full overflow-hidden border border-primary/20 p-0.5 shadow-sm group-hover:shadow-primary/20 transition-all duration-300">
              <img 
                src="https://images.unsplash.com/photo-1631885628966-a14af9faaa9b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx3b21hbiUyMHByb2ZpbGUlMjBwb3J0cmFpdHxlbnwxfHx8fDE3NzUxMDc0OTl8MA&ixlib=rb-4.1.0&q=80&w=1080" 
                alt="Profile"
                className="w-full h-full rounded-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-0 bg-background relative">
        <svg className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none z-50 mix-blend-multiply">
          <filter id="noiseFilter">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
          </filter>
          <rect width="100%" height="100%" filter="url(#noiseFilter)" />
        </svg>
        <div className="flex-1 overflow-y-auto z-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
