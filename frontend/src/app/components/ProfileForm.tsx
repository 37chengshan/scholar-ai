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
import toast from "react-hot-toast";

export function ProfileForm() {
  const [profile, setProfile] = useState<{
    name?: string;
    email?: string;
    avatar?: string;
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
      toast.error('Failed to load profile');
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
      toast.success('Profile updated');
    } catch (error: any) {
      console.error('Failed to update profile:', error);
      toast.error(error.response?.data?.error?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File size must be less than 5MB');
      return;
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('File must be an image');
      return;
    }

    try {
      setSaving(true);
      const result = await usersApi.uploadAvatar(file);
      setProfile(prev => prev ? { ...prev, avatar: result.avatar } : null);
      toast.success('Avatar uploaded');
    } catch (error: any) {
      console.error('Failed to upload avatar:', error);
      toast.error(error.response?.data?.error?.detail || 'Failed to upload avatar');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading profile...</div>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {/* Avatar Section */}
      <div className="flex flex-col gap-3">
        <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
          Avatar
        </label>
        <div className="flex items-center gap-4">
          <div className="w-20 h-20 rounded-full border-2 border-background overflow-hidden relative cursor-pointer shadow-md group">
            {profile?.avatar ? (
              <img
                src={profile.avatar}
                alt="Avatar"
                className="w-full h-full object-cover filter grayscale group-hover:grayscale-0 transition-all duration-700"
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
              type="file"
              accept="image/*"
              onChange={handleAvatarUpload}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
          </div>
          <div className="text-[10px] text-muted-foreground">
            <p>Click to upload new avatar</p>
            <p className="text-[9px] mt-1">JPEG, PNG, WebP • Max 5MB</p>
          </div>
        </div>
      </div>

      {/* Name Field */}
      <div className="flex flex-col gap-2">
        <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
          Name
        </label>
        <input
          type="text"
          value={profile?.name || ''}
          onChange={(e) => setProfile(prev => prev ? { ...prev, name: e.target.value } : null)}
          className="w-full bg-background border border-border/50 rounded-sm px-4 py-2.5 text-[12px] focus:outline-none focus:border-primary transition-colors shadow-sm"
          placeholder="Your name"
        />
      </div>

      {/* Email Field */}
      <div className="flex flex-col gap-2">
        <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">
          Email
        </label>
        <input
          type="email"
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
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  );
}