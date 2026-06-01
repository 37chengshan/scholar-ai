/**
 * ProfileForm Component
 *
 * User profile management form
 *
 * Features:
 * - Display and edit name, email
 * - Avatar upload
 * - Save changes to backend
 */

import { useState, useEffect } from "react";
import { Camera, Save } from "lucide-react";
import * as usersApi from "@/services/usersApi";
import { toast } from "sonner";

export function ProfileForm() {
  const avatarInputId = 'profile-avatar-upload';
  const profileNameInputId = 'profile-display-name';
  const profileEmailInputId = 'profile-email';

  const [profile, setProfile] = useState<{
    name?: string;
    email?: string;
    avatar?: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await usersApi.getProfile();
      setProfile({
        name: data.name,
        email: data.email,
        avatar: data.avatar,
      });
    } catch (error) {
      console.error('Failed to load profile:', error);
      toast.error('个人资料加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;

    try {
      setSaving(true);
      await usersApi.updateProfile(profile);
      toast.success('个人资料已更新');
    } catch (error: any) {
      console.error('Failed to update profile:', error);
      toast.error(error.response?.data?.error?.detail || '个人资料更新失败');
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('头像文件需小于 5MB');
      return;
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('仅支持上传图片文件');
      return;
    }

    try {
      setSaving(true);
      const result = await usersApi.uploadAvatar(file);
      setProfile(prev => prev ? { ...prev, avatar: result.avatar } : null);
      toast.success('头像已更新');
    } catch (error: any) {
      console.error('Failed to upload avatar:', error);
      toast.error(error.response?.data?.error?.detail || '头像上传失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">正在加载个人资料...</div>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {/* Avatar Section */}
      <div className="flex flex-col gap-3">
        <label htmlFor={avatarInputId} className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
          头像
        </label>
        <div className="flex items-center gap-4">
          <div className="w-20 h-20 rounded-full border-2 border-background overflow-hidden relative cursor-pointer shadow-md group">
            {profile?.avatar ? (
              <img
                src={profile.avatar}
                alt="用户头像"
                className="w-full h-full object-cover filter grayscale group-hover:grayscale-0 transition-[filter] duration-700"
              />
            ) : (
              <div className="w-full h-full bg-muted flex items-center justify-center">
                <Camera className="w-6 h-6 text-muted-foreground" />
              </div>
            )}
            <div className="absolute inset-0 bg-primary/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm">
              <Camera className="w-4 h-4 text-primary-foreground" />
            </div>
            <input
              id={avatarInputId}
              name="avatar"
              type="file"
              accept="image/*"
              onChange={handleAvatarUpload}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
          </div>
          <div className="text-[10px] text-muted-foreground">
            <p>点击上传新头像</p>
            <p className="text-[9px] mt-1">支持 JPEG、PNG、WebP，最大 5MB</p>
          </div>
        </div>
      </div>

      {/* Name Field */}
      <div className="flex flex-col gap-2">
        <label htmlFor={profileNameInputId} className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
          昵称
        </label>
        <input
          id={profileNameInputId}
          name="displayName"
          type="text"
          autoComplete="name"
          value={profile?.name || ''}
          onChange={(e) => setProfile(prev => prev ? { ...prev, name: e.target.value } : null)}
          className="w-full bg-background border border-border/50 rounded-sm px-4 py-2.5 text-[12px] focus:outline-none focus:border-primary transition-colors shadow-sm"
          placeholder="输入你的显示名称"
        />
      </div>

      {/* Email Field */}
      <div className="flex flex-col gap-2">
        <label htmlFor={profileEmailInputId} className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
          邮箱
        </label>
        <input
          id={profileEmailInputId}
          name="email"
          type="email"
          autoComplete="email"
          value={profile?.email || ''}
          onChange={(e) => setProfile(prev => prev ? { ...prev, email: e.target.value } : null)}
          className="w-full bg-background border border-border/50 rounded-sm px-4 py-2.5 text-[12px] focus:outline-none focus:border-primary transition-colors shadow-sm"
          placeholder="your@email.com"
        />
      </div>

      {/* Save Button */}
      <div className="flex justify-end pt-4">
        <button
          type="submit"
          disabled={saving}
          className="text-[9px] font-bold uppercase tracking-[0.2em] bg-primary text-primary-foreground px-6 py-2.5 rounded-sm hover:bg-secondary transition-colors shadow-sm flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="w-3 h-3" />
          {saving ? '保存中...' : '保存更改'}
        </button>
      </div>
    </form>
  );
}
