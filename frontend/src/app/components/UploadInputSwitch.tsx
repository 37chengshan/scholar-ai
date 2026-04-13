import { useLanguage } from '../contexts/LanguageContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

interface UploadInputSwitchProps {
  onFileSelect?: (files: FileList) => void;
  onOCRChange?: (enabled: boolean) => void;
}

/**
 * UploadInputSwitch Component
 *
 * Simplified to only support Local Files upload (per D-08).
 * URL/DOI and Zotero Sync tabs removed - backend endpoints not implemented.
 *
 * Follows UI-SPEC.md design constraints.
 */
export function UploadInputSwitch({ onFileSelect, onOCRChange }: UploadInputSwitchProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    localFiles: isZh ? "本地文件" : "Local Files",
    dropzone: isZh ? "拖放 PDF 文件到此处，或点击选择" : "Drag and drop PDF files here, or click to select",
    maxFiles: isZh ? "最多上传 50 个文件" : "Upload up to 50 files",
  };

  return (
    <Tabs defaultValue="local" className="w-full">
      <TabsList className="grid w-full grid-cols-1">
        <TabsTrigger value="local" className="text-sm font-semibold">
          {t.localFiles}
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
    </Tabs>
  );
}