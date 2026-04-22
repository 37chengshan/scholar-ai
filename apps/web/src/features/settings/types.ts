import type { LucideIcon } from 'lucide-react';

export type SettingsSectionId =
  | 'profile'
  | 'localization'
  | 'display'
  | 'security'
  | 'api'
  | 'diagnostics';

export interface SettingsSection {
  id: SettingsSectionId;
  label: string;
  icon: LucideIcon;
}
