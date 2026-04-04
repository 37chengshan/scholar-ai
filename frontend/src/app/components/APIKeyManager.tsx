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

import { useState, useEffect } from "react";
import { Plus, Trash2, Copy, Check, Eye, EyeOff } from "lucide-react";
import * as usersApi from "@/services/usersApi";
import toast from "react-hot-toast";

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsedAt?: string;
}

export function APIKeyManager() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      setLoading(true);
      const data = await usersApi.getApiKeys();
      setKeys(data);
    } catch (error) {
      console.error('Failed to load API keys:', error);
      toast.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }

    try {
      setCreating(true);
      const result = await usersApi.createApiKey(newKeyName);
      setNewlyCreatedKey(result.key);
      setNewKeyName('');
      await loadKeys();
      toast.success('API key created! Copy it now - it won\'t be shown again.');
    } catch (error: any) {
      console.error('Failed to create API key:', error);
      toast.error(error.response?.data?.error?.detail || 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (keyId: string) => {
    // Prompt for password
    const password = prompt('Enter your password to delete this API key:');
    if (!password) return;

    try {
      await usersApi.deleteApiKey(keyId, password);
      setKeys(keys.filter(k => k.id !== keyId));
      toast.success('API key deleted');
    } catch (error: any) {
      console.error('Failed to delete API key:', error);
      toast.error(error.response?.data?.error?.detail || 'Failed to delete API key');
    }
  };

  const handleCopyKey = async () => {
    if (!newlyCreatedKey) return;

    try {
      await navigator.clipboard.writeText(newlyCreatedKey);
      setCopied(true);
      toast.success('API key copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      toast.error('Failed to copy to clipboard');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading API keys...</div>;
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Create New Key */}
      <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col">
        <div className="p-5 border-b border-border/50 bg-muted/20">
          <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">
            Generate New API Key
          </h3>
          <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
            Create a new API key for programmatic access
          </p>
        </div>

        <div className="p-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="API key name (e.g., 'CLI tool', 'Integration')"
              className="flex-1 bg-background border border-border/50 rounded-sm px-4 py-2.5 text-[12px] focus:outline-none focus:border-primary transition-colors shadow-sm"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <button
              onClick={handleCreate}
              disabled={creating || !newKeyName.trim()}
              className="bg-primary text-primary-foreground px-4 py-2.5 rounded-sm text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-secondary transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-3 h-3" />
              {creating ? 'Creating...' : 'Generate'}
            </button>
          </div>

          <p className="text-[9px] text-muted-foreground mt-3">
            ⚠️ The full API key will only be shown once. Make sure to copy it immediately.
          </p>
        </div>
      </div>

      {/* Newly Created Key Display */}
      {newlyCreatedKey && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-sm p-5">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-green-600 mb-2">
                API Key Created Successfully
              </h4>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-background px-3 py-2 rounded text-[11px] font-mono">
                  {showKey ? newlyCreatedKey : '••••••••••••••••••••••••••••••••'}
                </code>
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="p-2 hover:bg-background rounded transition-colors"
                  title={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  onClick={handleCopyKey}
                  className="p-2 hover:bg-background rounded transition-colors"
                  title="Copy to clipboard"
                >
                  {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[9px] text-muted-foreground mt-2">
                Copy this key now. It won't be shown again for security reasons.
              </p>
            </div>
            <button
              onClick={() => setNewlyCreatedKey(null)}
              className="text-[9px] text-muted-foreground hover:text-foreground"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Existing Keys */}
      <div className="flex flex-col gap-3">
        <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">
          Your API Keys ({keys.length})
        </h3>

        {keys.length === 0 ? (
          <div className="text-center py-8 text-[10px] text-muted-foreground">
            No API keys yet. Create one above to get started.
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
                  <div>Created: {formatDate(key.createdAt)}</div>
                  {key.lastUsedAt && (
                    <div className="mt-1">Last used: {formatDate(key.lastUsedAt)}</div>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(key.id)}
                  className="p-2 text-red-500 hover:bg-red-500/10 rounded transition-colors"
                  title="Delete API key"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}