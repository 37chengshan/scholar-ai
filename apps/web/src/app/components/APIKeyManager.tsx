/**
 * APIKeyManager Component
 *
 * API key management interface
 *
 * Features:
 * - List existing API keys
 * - Generate new API keys (shows full key only once)
 * - Delete API keys (requires password confirmation)
 */

import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2, Copy, Check, Eye, EyeOff, KeyRound, AlertTriangle } from "lucide-react";
import * as usersApi from "@/services/usersApi";
import type { ApiKey } from "@/types";
import { toast } from "sonner";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { isTransportLevelApiFailure, resolveApiErrorMessage } from "@/utils/resolveApiErrorMessage";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog";

interface APIKeyManagerProps {
  isZh: boolean;
}

export function APIKeyManager({ isZh }: APIKeyManagerProps) {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ApiKey | null>(null);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleting, setDeleting] = useState(false);

  const labels = useMemo(() => ({
    loading: isZh ? '加载 API 密钥中...' : 'Loading API keys...',
    title: isZh ? '创建新的 API 密钥' : 'Generate New API Key',
    description: isZh ? '为自动化脚本、CLI 或集成创建编程访问凭据' : 'Create a new API key for programmatic access',
    inputPlaceholder: isZh ? '输入 API 密钥名称，例如“CLI 工具”或“集成服务”' : "API key name (e.g., 'CLI tool', 'Integration')",
    create: isZh ? '生成密钥' : 'Generate',
    creating: isZh ? '生成中...' : 'Creating...',
    oneTimeHint: isZh ? '完整密钥只会展示一次，请立即复制并妥善保存。' : "The full API key will only be shown once. Make sure to copy it immediately.",
    nameRequired: isZh ? '请输入 API 密钥名称' : 'Please enter a name for the API key',
    createdToast: isZh ? 'API 密钥已创建，请立即复制保存。' : "API key created! Copy it now - it won't be shown again.",
    loadError: isZh ? '暂时无法读取 API 密钥。可能是后端能力未启用，或服务当前返回异常。' : 'Unable to load API keys right now. The backend capability may be unavailable or the service may be failing.',
    createError: isZh ? '创建 API 密钥失败' : 'Failed to create API key',
    copied: isZh ? 'API 密钥已复制到剪贴板' : 'API key copied to clipboard',
    copyFailed: isZh ? '复制失败' : 'Failed to copy to clipboard',
    createdBanner: isZh ? 'API 密钥已创建' : 'API Key Created Successfully',
    copyNow: isZh ? '请现在复制，出于安全原因后续不会再次展示。' : "Copy this key now. It won't be shown again for security reasons.",
    dismiss: isZh ? '关闭' : 'Dismiss',
    yourKeys: isZh ? '现有 API 密钥' : 'Your API Keys',
    empty: isZh ? '还没有 API 密钥。先创建一个再开始。' : 'No API keys yet. Create one above to get started.',
    createdAt: isZh ? '创建于' : 'Created',
    lastUsedAt: isZh ? '上次使用' : 'Last used',
    deleteTitle: isZh ? '删除 API 密钥' : 'Delete API Key',
    deleteDescription: isZh ? '删除前需要再次输入当前登录密码进行确认。' : 'Re-enter your current password to confirm deletion.',
    deletePasswordLabel: isZh ? '当前密码' : 'Current Password',
    deletePasswordPlaceholder: isZh ? '输入当前密码以确认删除' : 'Enter your current password to confirm',
    deleteConfirm: isZh ? '确认删除' : 'Delete Key',
    deleting: isZh ? '删除中...' : 'Deleting...',
    deleteSuccess: isZh ? 'API 密钥已删除' : 'API key deleted',
    deleteError: isZh ? '删除 API 密钥失败' : 'Failed to delete API key',
    retry: isZh ? '重试' : 'Retry',
    hide: isZh ? '隐藏密钥' : 'Hide key',
    show: isZh ? '显示密钥' : 'Show key',
    copy: isZh ? '复制到剪贴板' : 'Copy to clipboard',
  }), [isZh]);

  useEffect(() => {
    void loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const data = await usersApi.getApiKeys();
      setKeys(data);
    } catch (error: unknown) {
      const message = resolveApiErrorMessage(error, labels.loadError);
      setLoadError(message);
      setKeys([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newKeyName.trim()) {
      toast.error(labels.nameRequired);
      return;
    }

    try {
      setCreating(true);
      const result = await usersApi.createApiKey(newKeyName);
      setNewlyCreatedKey(result.key);
      setNewKeyName('');
      await loadKeys();
      toast.success(labels.createdToast);
    } catch (error: unknown) {
      if (!isTransportLevelApiFailure(error)) {
        toast.error(resolveApiErrorMessage(error, labels.createError));
      }
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget || !deletePassword) {
      toast.error(labels.deletePasswordPlaceholder);
      return;
    }

    try {
      setDeleting(true);
      await usersApi.deleteApiKey(deleteTarget.id, deletePassword);
      setKeys(keys.filter((key) => key.id !== deleteTarget.id));
      setDeletePassword('');
      setDeleteTarget(null);
      toast.success(labels.deleteSuccess);
    } catch (error: unknown) {
      if (!isTransportLevelApiFailure(error)) {
        toast.error(resolveApiErrorMessage(error, labels.deleteError));
      }
    } finally {
      setDeleting(false);
    }
  };

  const handleCopyKey = async () => {
    if (!newlyCreatedKey) return;

    try {
      await navigator.clipboard.writeText(newlyCreatedKey);
      setCopied(true);
      toast.success(labels.copied);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(labels.copyFailed);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(isZh ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: isZh ? 'long' : 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">{labels.loading}</div>;
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Create New Key */}
      <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col">
        <div className="p-5 border-b border-border/50 bg-muted/20 flex items-center gap-3">
          <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
            <KeyRound className="w-3.5 h-3.5 text-primary" />
          </div>
          <div>
            <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em] font-serif tracking-tight">
              {labels.title}
            </h3>
            <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
              {labels.description}
            </p>
          </div>
        </div>

        <div className="p-6">
          <div className="flex gap-3">
            <Input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder={labels.inputPlaceholder}
              className="flex-1 rounded-sm"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <Button
              onClick={handleCreate}
              disabled={creating || !newKeyName.trim()}
              size="sm"
              className="h-11 rounded-sm px-4 text-[10px] font-bold uppercase tracking-[0.2em]"
            >
              <Plus className="w-3 h-3" />
              {creating ? labels.creating : labels.create}
            </Button>
          </div>

          <div className="mt-3 flex items-start gap-2 rounded-sm border border-border/50 bg-muted/20 p-3 text-[10px] text-muted-foreground">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 text-primary" />
            <p>{labels.oneTimeHint}</p>
          </div>
        </div>
      </div>

      {loadError ? (
        <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive space-y-3">
          <p>{loadError}</p>
          <Button type="button" variant="outline" size="sm" onClick={() => void loadKeys()}>
            {labels.retry}
          </Button>
        </div>
      ) : null}

      {/* Newly Created Key Display */}
      {newlyCreatedKey && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-sm p-5">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-green-600 mb-2">
                {labels.createdBanner}
              </h4>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-background px-3 py-2 rounded text-[11px] font-mono">
                  {showKey ? newlyCreatedKey : '••••••••••••••••••••••••••••••••'}
                </code>
                <Button
                  onClick={() => setShowKey(!showKey)}
                  type="button"
                  variant="ghost"
                  size="icon"
                  title={showKey ? labels.hide : labels.show}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
                <Button
                  onClick={handleCopyKey}
                  type="button"
                  variant="ghost"
                  size="icon"
                  title={labels.copy}
                >
                  {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
              <p className="text-[9px] text-muted-foreground mt-2">
                {labels.copyNow}
              </p>
            </div>
            <Button
              onClick={() => setNewlyCreatedKey(null)}
              type="button"
              variant="ghost"
              size="sm"
            >
              {labels.dismiss}
            </Button>
          </div>
        </div>
      )}

      {/* Existing Keys */}
      <div className="flex flex-col gap-3">
        <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 font-serif tracking-tight">
          {labels.yourKeys} ({keys.length})
        </h3>

        {keys.length === 0 ? (
          <div className="text-center py-8 text-[10px] text-muted-foreground">
            {labels.empty}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {keys.map((key) => (
              <div
                key={key.id}
                className="flex items-center gap-4 p-4 border border-border/50 rounded-sm bg-card hover:border-border transition-colors"
              >
                <div className="flex-1">
                  <div className="font-medium text-sm">{key.name}</div>
                  <div className="text-[9px] font-mono text-muted-foreground mt-1">
                    {key.prefix}...
                  </div>
                </div>
                <div className="text-[9px] text-muted-foreground text-right">
                  <div>{labels.createdAt}: {formatDate(key.createdAt)}</div>
                  {key.lastUsedAt && (
                    <div className="mt-1">{labels.lastUsedAt}: {formatDate(key.lastUsedAt)}</div>
                  )}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setDeleteTarget(key)}
                  className="p-2 text-red-500 hover:bg-red-500/10 rounded transition-colors"
                  title={labels.deleteTitle}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <Dialog open={deleteTarget !== null} onOpenChange={(open) => {
        if (!open) {
          setDeleteTarget(null);
          setDeletePassword('');
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{labels.deleteTitle}</DialogTitle>
            <DialogDescription>{labels.deleteDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="text-sm text-foreground">
              {deleteTarget?.name}
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                {labels.deletePasswordLabel}
              </label>
              <Input
                type="password"
                value={deletePassword}
                onChange={(event) => setDeletePassword(event.target.value)}
                placeholder={labels.deletePasswordPlaceholder}
                autoComplete="current-password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => {
              setDeleteTarget(null);
              setDeletePassword('');
            }}>
              {labels.dismiss}
            </Button>
            <Button type="button" variant="destructive" onClick={() => void handleDelete()} disabled={deleting}>
              {deleting ? labels.deleting : labels.deleteConfirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}