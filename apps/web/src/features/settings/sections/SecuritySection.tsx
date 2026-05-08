import { useState } from 'react';
import { LogOut, Shield } from 'lucide-react';
import { toast } from 'sonner';
import { ConfirmDialog } from '@/app/components/ConfirmDialog';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import * as usersApi from '@/services/usersApi';
import { isTransportLevelApiFailure, resolveApiErrorMessage } from '@/utils/resolveApiErrorMessage';

interface SecuritySectionProps {
  isZh: boolean;
  onLogout: (options?: { silentSuccess?: boolean }) => Promise<void>;
}

export function SecuritySection({ isZh, onLogout }: SecuritySectionProps) {
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const labels = {
    authTitle: isZh ? '身份验证' : 'Authentication',
    authDescription: isZh ? '更新登录密钥并重新验证当前会话' : 'Update your login credentials and re-verify the current session',
    currentPassword: isZh ? '当前密码' : 'Current Password',
    newPassword: isZh ? '新密码' : 'New Password',
    confirmPassword: isZh ? '确认新密码' : 'Confirm New Password',
    currentPlaceholder: isZh ? '输入当前密码' : 'Enter current password',
    newPlaceholder: isZh ? '至少 8 个字符，包含大小写字母和数字' : 'At least 8 chars with upper, lower, and number',
    confirmPlaceholder: isZh ? '再次输入新密码' : 'Re-enter new password',
    updatePassword: isZh ? '更新密码' : 'Update Password',
    updatingPassword: isZh ? '更新中...' : 'Updating...',
    logoutTitle: isZh ? '登出' : 'Logout',
    logoutDescription: isZh ? '结束当前会话' : 'End your current session',
    validationEmpty: isZh ? '请填写所有密码字段' : 'Please fill in all password fields',
    validationLength: isZh ? '密码至少需要 8 个字符' : 'Password must be at least 8 characters',
    validationMismatch: isZh ? '两次输入的新密码不一致' : 'New passwords do not match',
    success: isZh ? '密码已更新，请重新登录' : 'Password updated. Please sign in again.',
    fallbackError: isZh ? '密码更新失败' : 'Failed to update password',
  };

  const handlePasswordUpdate = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error(labels.validationEmpty);
      return;
    }

    if (newPassword.length < 8) {
      toast.error(labels.validationLength);
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error(labels.validationMismatch);
      return;
    }

    try {
      setIsSubmitting(true);
      await usersApi.changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast.success(labels.success);
      await onLogout({ silentSuccess: true });
    } catch (error: unknown) {
      if (!isTransportLevelApiFailure(error)) {
        toast.error(resolveApiErrorMessage(error, labels.fallbackError));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
        <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
          <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
            <Shield className="w-3.5 h-3.5 text-destructive" />
          </div>
          <div>
            <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em] font-serif tracking-tight">
              {labels.authTitle}
            </h3>
            <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
              {labels.authDescription}
            </p>
          </div>
        </div>

        <div className="p-6 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
              {labels.currentPassword}
            </label>
            <Input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              placeholder={labels.currentPlaceholder}
              autoComplete="current-password"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
              {labels.newPassword}
            </label>
            <Input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder={labels.newPlaceholder}
              autoComplete="new-password"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
              {labels.confirmPassword}
            </label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder={labels.confirmPlaceholder}
              autoComplete="new-password"
            />
          </div>
          <Button
            type="button"
            onClick={() => void handlePasswordUpdate()}
            disabled={isSubmitting}
            className="w-full justify-center"
          >
            {isSubmitting ? labels.updatingPassword : labels.updatePassword}
          </Button>
        </div>
      </div>

      <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
        <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
          <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
            <LogOut className="w-3.5 h-3.5 text-destructive" />
          </div>
          <div>
            <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em] font-serif tracking-tight">{isZh ? '登出' : 'Logout'}</h3>
            <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
              {labels.logoutDescription}
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
            {labels.logoutTitle}
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
