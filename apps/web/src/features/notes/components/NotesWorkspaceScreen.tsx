import { WorkspaceShell } from '@/app/components/layout/WorkspaceShell';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/app/components/ui/alert-dialog';
import { NotesHeader } from '@/features/notes/components/NotesHeader';
import { NotesMainPanel } from '@/features/notes/components/NotesMainPanel';
import { NotesSaveIndicator } from '@/features/notes/components/NotesSaveIndicator';
import { NotesSidebar } from '@/features/notes/components/NotesSidebar';
import { useNotesWorkspace } from '@/features/notes/hooks/useNotesWorkspace';

export function NotesWorkspaceScreen() {
  const {
    headerProps,
    sidebarProps,
    mainPanelProps,
    saveIndicatorProps,
    deleteDialogProps,
  } = useNotesWorkspace();

  return (
    <div className="editorial-app-shell relative min-h-screen bg-background">
      <NotesHeader {...headerProps} />

      <div className="h-[calc(100vh-10rem)] bg-background/50">
        <WorkspaceShell
          layoutId="notes"
          sidebar={<NotesSidebar {...sidebarProps} />}
          main={(
            <NotesMainPanel
              {...mainPanelProps}
              saveIndicator={<NotesSaveIndicator {...saveIndicatorProps} />}
            />
          )}
        />
      </div>

      <AlertDialog open={deleteDialogProps.open} onOpenChange={deleteDialogProps.onOpenChange}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>此操作不可撤销</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={deleteDialogProps.onConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
