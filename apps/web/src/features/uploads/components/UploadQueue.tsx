import { UploadQueueItem as UploadQueueItemModel } from '@/features/uploads/state/uploadWorkspaceStore';
import { UploadQueueItem } from './UploadQueueItem';

interface UploadQueueProps {
  items: UploadQueueItemModel[];
  onRemove: (id: string) => void;
  onCancel?: (item: UploadQueueItemModel) => void;
  removable: boolean;
}

export function UploadQueue({ items, onRemove, onCancel, removable }: UploadQueueProps) {
  if (items.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/70 px-4 py-6 text-center text-sm text-muted-foreground">
        暂无待上传文件
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
      {items.map((item) => (
        <UploadQueueItem key={item.id} item={item} onRemove={onRemove} onCancel={onCancel} removable={removable} />
      ))}
    </div>
  );
}
