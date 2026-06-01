import { Link } from "react-router";
import { LogOut, Settings } from "lucide-react";
import { clsx } from "clsx";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";

function getUserInitials(name?: string | null) {
  if (!name) return "SA";
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) return "SA";
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("");
}

interface UserProfileProps {
  userName?: string | null;
  userAvatar?: string | null;
  isZh: boolean;
  leftCollapsed: boolean;
  onLogout: () => void;
  onNavigate: () => void;
}

export function UserProfile({
  userName,
  userAvatar,
  isZh,
  leftCollapsed,
  onLogout,
  onNavigate,
}: UserProfileProps) {
  return (
    <div className={clsx("flex items-center", leftCollapsed ? "flex-col gap-2 px-0 py-0" : "gap-2 px-2 py-2")}>
      <Avatar className="h-8 w-8 shrink-0 rounded-md border border-border/70 bg-card shadow-sm">
        <AvatarImage src={userAvatar ?? undefined} alt={userName || "User"} className="object-cover" />
        <AvatarFallback className="rounded-md bg-muted font-sans text-[10px] font-bold uppercase tracking-[0.18em] text-foreground/70">
          {getUserInitials(userName)}
        </AvatarFallback>
      </Avatar>
      {!leftCollapsed ? (
        <div className="min-w-0 flex-1">
          <div className="text-[8.5px] font-bold uppercase tracking-[0.18em] text-muted-foreground/80">
            {isZh ? "账号" : "Profile"}
          </div>
          <div className="truncate text-[12.5px] font-semibold leading-tight text-foreground/90">
            {userName || (isZh ? "研究者" : "Scholar")}
          </div>
        </div>
      ) : null}
      <Link
        to="/settings"
        onClick={onNavigate}
        title={isZh ? "打开设置" : "Open settings"}
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-background text-foreground/60 transition-all duration-150 hover:border-primary/25 hover:text-primary hover:bg-primary/[0.04]"
        aria-label={isZh ? "打开设置" : "Open settings"}
      >
        <Settings className="h-3.5 w-3.5" />
      </Link>
      <button
        type="button"
        onClick={onLogout}
        title={isZh ? "退出登录" : "Log out"}
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-paper-2 text-foreground/60 transition-colors hover:border-primary/20 hover:text-primary"
        aria-label={isZh ? "退出登录" : "Log out"}
      >
        <LogOut className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
