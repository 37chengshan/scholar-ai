import { useEffect, useState } from 'react';

import { Button } from './ui/button';
import { Input } from './ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

interface LinkUrlDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  inputLabel: string;
  placeholder: string;
  confirmLabel: string;
  clearLabel: string;
  cancelLabel: string;
  initialValue?: string;
  onConfirm: (value: string) => void;
  onClear?: () => void;
}

export function LinkUrlDialog({
  open,
  onOpenChange,
  title,
  description,
  inputLabel,
  placeholder,
  confirmLabel,
  clearLabel,
  cancelLabel,
  initialValue = '',
  onConfirm,
  onClear,
}: LinkUrlDialogProps) {
  const [value, setValue] = useState(initialValue);

  useEffect(() => {
    if (open) {
      setValue(initialValue);
    }
  }, [initialValue, open]);

  const trimmedValue = value.trim();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <label htmlFor="link-url-input" className="text-sm font-medium text-foreground">
            {inputLabel}
          </label>
          <Input
            id="link-url-input"
            type="url"
            inputMode="url"
            autoComplete="url"
            placeholder={placeholder}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && trimmedValue) {
                event.preventDefault();
                onConfirm(trimmedValue);
                onOpenChange(false);
              }
            }}
          />
        </div>

        <DialogFooter>
          {onClear ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                onClear();
                onOpenChange(false);
              }}
            >
              {clearLabel}
            </Button>
          ) : null}
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            {cancelLabel}
          </Button>
          <Button
            type="button"
            onClick={() => {
              onConfirm(trimmedValue);
              onOpenChange(false);
            }}
            disabled={!trimmedValue}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}