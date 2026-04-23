import { useState } from 'react';
import { LogOut, Shield } from 'lucide-react';
import { ConfirmDialog } from '@/app/components/ConfirmDialog';

interface SecuritySectionProps {
  isZh: boolean;
  onLogout: () => Promise<void>;
}

export function SecuritySection({ isZh, onLogout }: SecuritySectionProps) {
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  return (
    <>
      <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
        <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
          <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
            <Shield className="w-3.5 h-3.5 text-destructive" />
          </div>
          <div>
            <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">
              {isZh ? '身份验证' : 'Authentication'}
            </h3>
            <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
              {isZh ? '需要 Level 4 权限' : 'Level 4 clearance required'}
            </p>
          </div>
        </div>

        <div className="p-6 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
              {isZh ? '当前密钥' : 'Current Passkey'}
            </label>
            <input
              type="password"
              defaultValue="********"
              className="w-full bg-background border-b-2 border-border/50 rounded-t-sm px-3 py-3 text-[14px] font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors bg-transparent"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
              {isZh ? '新密钥' : 'New Passkey'}
            </label>
            <input
              type="password"
              placeholder={isZh ? '输入新密钥' : 'ENTER NEW KEY'}
              className="w-full bg-background border-b-2 border-border/50 rounded-t-sm px-3 py-3 text-[14px] font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors bg-transparent placeholder:text-muted-foreground/30"
            />
          </div>
        </div>
      </div>

      <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
        <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
          <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
            <LogOut className="w-3.5 h-3.5 text-destructive" />
          </div>
          <div>
            <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">{isZh ? '登出' : 'Logout'}</h3>
            <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
              {isZh ? '结束当前会话' : 'End your current session'}
            </p>
          </div>
        </div>

        <div className="p-6">
          <button
            onClick={() => setShowLogoutConfirm(true)}
            data-testid="logout-button"
            className="w-full bg-destructive/10 border border-destructive/20 text-destructive hover:bg-destructive hover:text-destructive-foreground px-4 py-3 rounded-sm transition-colors flex items-center justify-center gap-2 text-sm font-bold uppercase tracking-widest"
          >
            <LogOut className="w-4 h-4" />
            {isZh ? '登出' : 'Logout'}
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showLogoutConfirm}
        title={isZh ? '退出登录' : 'Logout'}
        message={
          isZh
            ? '确定要退出登录吗？退出后需要重新登录才能使用。'
            : 'Are you sure you want to logout? You will need to login again to use the system.'
        }
        confirmLabel={isZh ? '退出' : 'Logout'}
        cancelLabel={isZh ? '取消' : 'Cancel'}
        variant="danger"
        onConfirm={async () => {
          setShowLogoutConfirm(false);
          await onLogout();
        }}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </>
  );
}
