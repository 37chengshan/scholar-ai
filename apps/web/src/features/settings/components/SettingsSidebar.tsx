import { Camera, Box } from 'lucide-react';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { Avatar, AvatarFallback, AvatarImage } from '@/app/components/ui/avatar';
import type { SettingsSection, SettingsSectionId } from '@/features/settings/types';

interface SettingsSidebarProps {
  title: string;
  subtitle: string;
  userName: string;
  userId: string;
  userAvatar?: string;
  sections: SettingsSection[];
  activeSection: SettingsSectionId;
  onSectionChange: (section: SettingsSectionId) => void;
}

export function SettingsSidebar({
  title,
  subtitle,
  userName,
  userId,
  userAvatar,
  sections,
  activeSection,
  onSectionChange,
}: SettingsSidebarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
      className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
    >
      <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
        <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{title}</h2>
        <Box className="w-4 h-4 text-primary" />
      </div>

      <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
        <div className="flex flex-col items-center gap-3 pb-6 border-b border-border/50">
          <div className="relative cursor-pointer group">
            <Avatar className="h-20 w-20 rounded-full border-2 border-background shadow-md">
              <AvatarImage
                src={userAvatar}
                alt={userName}
                className="object-cover filter grayscale group-hover:grayscale-0 transition-all duration-700"
              />
              <AvatarFallback className="bg-paper-2 text-lg font-semibold tracking-[0.18em] text-foreground/70">
                {getUserInitials(userName)}
              </AvatarFallback>
            </Avatar>
            <div className="absolute inset-0 bg-primary/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm">
              <Camera className="w-4 h-4 text-primary-foreground" />
            </div>
          </div>
          <div className="text-center">
            <div className="font-serif text-lg font-black leading-tight">{userName}</div>
            <div className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground mt-1">ID: {userId}</div>
          </div>
        </div>

        <div>
          <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{subtitle}</div>
          <div className="flex flex-col gap-1">
            {sections.map((item) => (
              <button
                key={item.id}
                onClick={() => onSectionChange(item.id)}
                className={clsx(
                  'flex items-center gap-2.5 px-3 py-2 rounded-sm transition-colors group w-full text-left',
                  activeSection === item.id
                    ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20'
                    : 'hover:bg-card border border-transparent hover:border-border/50 text-foreground/80 hover:text-primary',
                )}
              >
                <item.icon className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1">{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function getUserInitials(name?: string | null) {
  if (!name) return 'SA';
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) return 'SA';
  return parts.map((part) => part[0]?.toUpperCase() ?? '').join('');
}
