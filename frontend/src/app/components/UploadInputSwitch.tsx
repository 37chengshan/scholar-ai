import { useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';

interface UploadInputSwitchProps {
  onFileSelect?: (files: FileList) => void;
  onOCRChange?: (enabled: boolean) => void;
}

/**
 * UploadInputSwitch Component
 *
 * Tabs for selecting upload input mode (D-12):
 * - Local Files (active, drag-drop zone)
 * - URL/DOI (disabled, shows "Coming soon")
 * - Zotero Sync (disabled, shows "Coming soon")
 *
 * Follows UI-SPEC.md design constraints.
 */
export function UploadInputSwitch({ onFileSelect, onOCRChange }: UploadInputSwitchProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const [showComingSoonDialog, setComingSoonDialog] = useState(false);
  const [comingSoonFeature, setComingSoonFeature] = useState('');

  const t = {
    localFiles: isZh ? "本地文件" : "Local Files",
    urlDoi: isZh ? "URL/DOI" : "URL/DOI",
    zotero: isZh ? "Zotero 同步" : "Zotero Sync",
    dropzone: isZh ? "拖放 PDF 文件到此处，或点击选择" : "Drag and drop PDF files here, or click to select",
    maxFiles: isZh ? "最多上传 50 个文件" : "Upload up to 50 files",
    comingSoon: isZh ? "正在开发" : "Coming Soon",
    comingSoonTitle: isZh ? "功能开发中" : "Feature Under Development",
    comingSoonDesc: isZh ? "此功能正在积极开发中，敬请期待！" : "This feature is under active development. Stay tuned!",
  };

  const handleDisabledTabClick = (feature: string) => {
    setComingSoonFeature(feature);
    setComingSoonDialog(true);
  };

  return (
    <>
      <Tabs defaultValue="local" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="local" className="text-sm font-semibold">
            {t.localFiles}
          </TabsTrigger>
          <TabsTrigger
            value="url"
            className="text-sm font-semibold opacity-50 cursor-not-allowed"
            onClick={(e) => {
              e.preventDefault();
              handleDisabledTabClick(t.urlDoi);
            }}
          >
            {t.urlDoi}
          </TabsTrigger>
          <TabsTrigger
            value="zotero"
            className="text-sm font-semibold opacity-50 cursor-not-allowed"
            onClick={(e) => {
              e.preventDefault();
              handleDisabledTabClick(t.zotero);
            }}
          >
            {t.zotero}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="local" className="mt-4">
          <div className="border-2 border-dashed border-[#f4ece1] rounded-sm p-12 text-center hover:border-[#d35400] transition-colors cursor-pointer bg-[#fdfaf6]">
            <input
              type="file"
              multiple
              accept=".pdf"
              className="hidden"
              id="file-upload"
              onChange={(e) => e.target.files && onFileSelect?.(e.target.files)}
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <p className="text-base font-semibold mb-2">{t.dropzone}</p>
              <p className="text-sm text-muted-foreground">{t.maxFiles}</p>
            </label>
          </div>
        </TabsContent>

        <TabsContent value="url" className="mt-4">
          {/* Disabled - placeholder */}
        </TabsContent>

        <TabsContent value="zotero" className="mt-4">
          {/* Disabled - placeholder */}
        </TabsContent>
      </Tabs>

      {/* Coming Soon Dialog */}
      <Dialog open={showComingSoonDialog} onOpenChange={setComingSoonDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold">{t.comingSoonTitle}</DialogTitle>
            <DialogDescription className="text-base">
              {t.comingSoonDesc}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-center py-4">
            <span className="text-[#d35400] text-sm font-semibold">{comingSoonFeature} - {t.comingSoon}</span>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}