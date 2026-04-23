import { useMemo, useState } from 'react';
import { Activity, Globe, Key, Lock, Monitor, User } from 'lucide-react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { useSettingsStore } from '@/stores/settingsStore';
import { useAuth } from '@/contexts/AuthContext';
import { SettingsSidebar } from '@/features/settings/components/SettingsSidebar';
import { SettingsSectionLayout } from '@/features/settings/components/SettingsSectionLayout';
import { SettingsStatusRail } from '@/features/settings/components/SettingsStatusRail';
import { ProfileSection } from '@/features/settings/sections/ProfileSection';
import { LocalizationSection } from '@/features/settings/sections/LocalizationSection';
import { DisplaySection } from '@/features/settings/sections/DisplaySection';
import { ApiSection } from '@/features/settings/sections/ApiSection';
import { DiagnosticsSection } from '@/features/settings/sections/DiagnosticsSection';
import { SecuritySection } from '@/features/settings/sections/SecuritySection';
import type { SettingsSectionId } from '@/features/settings/types';

export function Settings() {
  const [activeSection, setActiveSection] = useState<SettingsSectionId>('profile');
  const { fontSize, setFontSize } = useSettingsStore();
  const { language, setLanguage } = useLanguage();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isZh = language === 'zh';

  const labels = useMemo(() => ({
    system: isZh ? '系统' : 'System',
    preferences: isZh ? '偏好设置' : 'Preferences',
    configVer: isZh ? '配置 v2.4.1' : 'Configuration v2.4.1',
    diagnostics: isZh ? '系统诊断' : 'Diagnostics',
    storageUsage: isZh ? '存储使用量' : 'Storage Usage',
    storageHint: isZh ? '存储监控功能暂不提供' : 'Storage monitoring not available',
    systemStream: isZh ? '系统流' : 'System Stream',
    sections: {
      profile: isZh ? '个人资料' : 'Profile Data',
      localization: isZh ? '语言设置' : 'Localization',
      display: isZh ? '显示设置' : 'Display',
      security: isZh ? '安全设置' : 'Security',
      api: isZh ? 'API 集成' : 'API Integrations',
      diagnostics: isZh ? '系统诊断' : 'Diagnostics',
    },
  }), [isZh]);

  const sections = useMemo(() => ([
    { id: 'profile' as const, label: labels.sections.profile, icon: User },
    { id: 'localization' as const, label: labels.sections.localization, icon: Globe },
    { id: 'display' as const, label: labels.sections.display, icon: Monitor },
    { id: 'security' as const, label: labels.sections.security, icon: Lock },
    { id: 'api' as const, label: labels.sections.api, icon: Key },
    { id: 'diagnostics' as const, label: labels.sections.diagnostics, icon: Activity },
  ]), [labels.sections]);

  const handleLogout = async () => {
    try {
      await logout();
      toast.success(isZh ? '已登出' : 'Logged out successfully');
      navigate('/login');
    } catch {
      toast.error(isZh ? '登出失败' : 'Logout failed');
    }
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      <SettingsSidebar
        title={labels.system}
        subtitle={labels.preferences}
        userName={user?.name || (isZh ? '用户' : 'User')}
        userId={user?.id || '—'}
        userAvatar={user?.avatar ?? undefined}
        sections={sections}
        activeSection={activeSection}
        onSectionChange={setActiveSection}
      />

      <SettingsSectionLayout title={labels.sections[activeSection]} versionLabel={labels.configVer}>
        {activeSection === 'profile' ? <ProfileSection /> : null}
        {activeSection === 'localization' ? (
          <LocalizationSection
            language={language}
            setLanguage={setLanguage}
          />
        ) : null}
        {activeSection === 'display' ? (
          <DisplaySection fontSize={fontSize} setFontSize={setFontSize} />
        ) : null}
        {activeSection === 'api' ? <ApiSection /> : null}
        {activeSection === 'diagnostics' ? <DiagnosticsSection /> : null}
        {activeSection === 'security' ? <SecuritySection isZh={isZh} onLogout={handleLogout} /> : null}
      </SettingsSectionLayout>

      <SettingsStatusRail
        diagnosticsLabel={labels.diagnostics}
        storageUsageLabel={labels.storageUsage}
        storageHint={labels.storageHint}
        streamLabel={labels.systemStream}
      />
    </div>
  );
}
