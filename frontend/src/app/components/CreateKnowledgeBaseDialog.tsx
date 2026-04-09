import { useState } from "react";
import { motion } from "motion/react";
import { Brain, Network, FileText, Image, Search, BarChart3 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Checkbox } from "../components/ui/checkbox";
import { Separator } from "../components/ui/separator";
import { Label } from "../components/ui/label";

export interface CreateKBData {
  name: string;
  description: string;
  category: string;
  embeddingModel: string;
  chunkStrategy: string;
  enableGraph: boolean;
  enableImrad: boolean;
  enableChartUnderstanding: boolean;
  enableMultimodalSearch: boolean;
  enableComparison: boolean;
  parseEngine: string;
}

interface CreateKnowledgeBaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: CreateKBData) => void;
}

const defaultData: CreateKBData = {
  name: "",
  description: "",
  category: "人工智能",
  embeddingModel: "bge-m3",
  chunkStrategy: "by-paragraph",
  enableGraph: true,
  enableImrad: true,
  enableChartUnderstanding: false,
  enableMultimodalSearch: false,
  enableComparison: true,
  parseEngine: "docling",
};

const enhancementFeatures = [
  {
    key: "enableGraph" as const,
    icon: Network,
    label: "知识图谱构建",
    description: "自动提取实体关系",
  },
  {
    key: "enableImrad" as const,
    icon: FileText,
    label: "IMRaD 结构提取",
    description: "提取论文结构信息",
  },
  {
    key: "enableChartUnderstanding" as const,
    icon: Image,
    label: "图表理解",
    description: "解析论文中的图表",
  },
  {
    key: "enableMultimodalSearch" as const,
    icon: Search,
    label: "多模态检索",
    description: "支持图片/表格检索",
  },
  {
    key: "enableComparison" as const,
    icon: BarChart3,
    label: "对比分析",
    description: "启用多论文对比功能",
  },
];

export function CreateKnowledgeBaseDialog({
  open,
  onOpenChange,
  onCreate,
}: CreateKnowledgeBaseDialogProps) {
  const [form, setForm] = useState<CreateKBData>(defaultData);
  const [errors, setErrors] = useState<{ name?: string; description?: string }>({});

  const updateField = <K extends keyof CreateKBData>(key: K, value: CreateKBData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    // Clear error when user types
    if (errors[key as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    }
  };

  const handleSubmit = () => {
    const newErrors: { name?: string; description?: string } = {};
    if (!form.name.trim()) {
      newErrors.name = "请输入知识库名称";
    }
    if (!form.description.trim()) {
      newErrors.description = "请输入知识库描述";
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    onCreate(form);
    setForm(defaultData);
    setErrors({});
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setForm(defaultData);
      setErrors({});
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl font-semibold flex items-center gap-2">
            <Brain className="h-5 w-5" />
            创建知识库
          </DialogTitle>
          <DialogDescription>
            配置您的研究方向知识库，设置解析和向量化参数
          </DialogDescription>
        </DialogHeader>

        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.2 }}>
        <div className="flex flex-col gap-6 py-4">
          {/* 基础设置 */}
          <div className="flex flex-col gap-4">
            <h3 className="font-serif text-sm font-semibold text-foreground">基础设置</h3>

            <div className="flex flex-col gap-2">
              <Label htmlFor="kb-name">
                知识库名称 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="kb-name"
                placeholder="请输入研究方向名称，如：大语言模型对齐研究"
                value={form.name}
                maxLength={50}
                onChange={(e) => updateField("name", e.target.value)}
              />
              <div className="flex justify-end text-xs text-muted-foreground">
                {form.name.length}/50
              </div>
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="kb-desc">
                知识库描述 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="kb-desc"
                placeholder="描述该知识库的研究方向和内容范围，这将帮助 AI 更好地理解上下文..."
                value={form.description}
                maxLength={200}
                rows={3}
                onChange={(e) => updateField("description", e.target.value)}
              />
              <div className="flex justify-end text-xs text-muted-foreground">
                {form.description.length}/200
              </div>
              {errors.description && (
                <p className="text-xs text-destructive">{errors.description}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label>研究方向分类</Label>
              <Select
                value={form.category}
                onValueChange={(v) => updateField("category", v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择研究方向" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="人工智能">人工智能</SelectItem>
                  <SelectItem value="自然语言处理">自然语言处理</SelectItem>
                  <SelectItem value="计算机视觉">计算机视觉</SelectItem>
                  <SelectItem value="机器学习">机器学习</SelectItem>
                  <SelectItem value="其他">其他</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator />

          {/* 向量化配置 */}
          <div className="flex flex-col gap-4">
            <h3 className="font-serif text-sm font-semibold text-foreground">向量化配置</h3>

            <div className="flex flex-col gap-2">
              <Label>嵌入模型</Label>
              <Select
                value={form.embeddingModel}
                onValueChange={(v) => updateField("embeddingModel", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bge-m3">BGE-M3（推荐）</SelectItem>
                  <SelectItem value="text-embedding-3-large">
                    text-embedding-3-large
                  </SelectItem>
                  <SelectItem value="text-embedding-3-small">
                    text-embedding-3-small
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <Label>切片策略</Label>
              <Select
                value={form.chunkStrategy}
                onValueChange={(v) => updateField("chunkStrategy", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="by-paragraph">按段落切片（推荐）</SelectItem>
                  <SelectItem value="fixed-length">固定长度切片</SelectItem>
                  <SelectItem value="by-heading">按标题切片</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator />

          {/* 增强功能 */}
          <div className="flex flex-col gap-4">
            <h3 className="font-serif text-sm font-semibold text-foreground">增强功能</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {enhancementFeatures.map((feature) => (
                <div
                  key={feature.key}
                  className="flex items-start gap-3 rounded-lg border border-border/50 p-3 bg-card"
                >
                  <Checkbox
                    id={feature.key}
                    checked={form[feature.key] as boolean}
                    onCheckedChange={(checked) =>
                      updateField(feature.key, checked as boolean)
                    }
                  />
                  <div className="flex flex-col gap-0.5">
                    <Label
                      htmlFor={feature.key}
                      className="flex items-center gap-1.5 text-sm font-medium cursor-pointer"
                    >
                      <feature.icon className="h-3.5 w-3.5 text-muted-foreground" />
                      {feature.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* 解析引擎 */}
          <div className="flex flex-col gap-4">
            <h3 className="font-serif text-sm font-semibold text-foreground">解析引擎</h3>

            <div className="flex flex-col gap-2">
              <Label>解析引擎</Label>
              <Select
                value={form.parseEngine}
                onValueChange={(v) => updateField("parseEngine", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="docling">Docling（推荐）</SelectItem>
                  <SelectItem value="mineru">MinerU</SelectItem>
                  <SelectItem value="simple-text">简单文本</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        </motion.div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit}>创建知识库</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
