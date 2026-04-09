import { useState } from "react";
import { useNavigate } from "react-router";
import { Grid, List, Search, Plus, HardDrive } from "lucide-react";
import { KnowledgeBaseCard } from "../components/KnowledgeBaseCard";
import { CreateKnowledgeBaseDialog } from "../components/CreateKnowledgeBaseDialog";
import { ImportKnowledgeDialog } from "../components/ImportKnowledgeDialog";
import { EmptyState } from "../components/EmptyState";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { MoreHorizontal, ArrowRight, Download, Pencil, Trash2, Network } from "lucide-react";
import { toast } from "sonner";

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  paperCount: number;
  chunkCount: number;
  entityCount: number;
  updatedAt: string;
  category: string;
}

const MOCK_KNOWLEDGE_BASES: KnowledgeBase[] = [
  {
    id: "kb-001",
    name: "大语言模型对齐研究",
    description: "研究 LLM 对齐方法，包括 RLHF、DPO、Constitutional AI 等主流对齐技术及其比较分析",
    paperCount: 12,
    chunkCount: 3200,
    entityCount: 156,
    updatedAt: "2026-04-09",
    category: "人工智能",
  },
  {
    id: "kb-002",
    name: "多模态学习综述",
    description: "视觉-语言模型最新进展，包括 CLIP、BLIP、Flamingo 等多模态架构的对比研究",
    paperCount: 8,
    chunkCount: 1800,
    entityCount: 89,
    updatedAt: "2026-03-15",
    category: "计算机视觉",
  },
  {
    id: "kb-003",
    name: "Agent 框架对比",
    description: "智能体架构对比分析，包括 ReAct、AutoGPT、LangChain 等框架的设计模式和最佳实践",
    paperCount: 5,
    chunkCount: 960,
    entityCount: 42,
    updatedAt: "2026-02-20",
    category: "人工智能",
  },
  {
    id: "kb-004",
    name: "毕业论文文献整理",
    description: "博士论文相关文献，涵盖知识图谱、RAG 系统、信息抽取等核心研究方向",
    paperCount: 23,
    chunkCount: 5100,
    entityCount: 234,
    updatedAt: "2026-04-01",
    category: "自然语言处理",
  },
  {
    id: "kb-005",
    name: "课程阅读材料",
    description: "研究生课程推荐阅读材料，包括深度学习基础、强化学习入门等经典论文",
    paperCount: 15,
    chunkCount: 2400,
    entityCount: 0,
    updatedAt: "2026-01-10",
    category: "机器学习",
  },
];

type ViewMode = "card" | "list";

export function KnowledgeBaseList() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<ViewMode>("card");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [importTarget, setImportTarget] = useState<{ id: string; name: string } | null>(null);

  // Filter knowledge bases
  const filtered = MOCK_KNOWLEDGE_BASES.filter((kb) => {
    const matchesSearch =
      searchQuery === "" ||
      kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      kb.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      categoryFilter === "all" || kb.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleCreate = () => {
    setShowCreateDialog(true);
  };

  const handleCreateSubmit = (data: any) => {
    toast.success(`知识库「${data.name}」创建成功`);
    setShowCreateDialog(false);
  };

  const handleEnter = (id: string) => {
    navigate(`/knowledge-bases/${id}`);
  };

  const handleImport = (id: string, name: string) => {
    setImportTarget({ id, name });
  };

  const handleEdit = (name: string) => {
    toast.info(`编辑「${name}」功能开发中`);
  };

  const handleDelete = (name: string) => {
    toast.info(`删除「${name}」功能开发中`);
  };

  // Storage mock
  const storageUsed = "1.2GB";
  const storageTotal = "5GB";

  return (
    <div className="min-h-screen bg-background">
      {/* Top Toolbar */}
      <div className="border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-semibold text-foreground">知识库</h1>
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <HardDrive className="h-4 w-4" />
              <span>存储 {storageUsed} / {storageTotal}</span>
            </div>
          </div>
          <Button onClick={handleCreate} className="gap-2">
            <Plus className="h-4 w-4" />
            创建知识库
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="w-48">
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger>
                <SelectValue placeholder="全部研究方向" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部研究方向</SelectItem>
                <SelectItem value="人工智能">人工智能</SelectItem>
                <SelectItem value="自然语言处理">自然语言处理</SelectItem>
                <SelectItem value="计算机视觉">计算机视觉</SelectItem>
                <SelectItem value="机器学习">机器学习</SelectItem>
                <SelectItem value="其他">其他</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索知识库名称或描述..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <div className="flex items-center gap-1 ml-auto">
            <Button
              variant={viewMode === "card" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("card")}
              className="gap-1.5"
            >
              <Grid className="h-4 w-4" />
              卡片
            </Button>
            <Button
              variant={viewMode === "list" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("list")}
              className="gap-1.5"
            >
              <List className="h-4 w-4" />
              列表
            </Button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="max-w-7xl mx-auto px-6 pb-12">
        {filtered.length === 0 ? (
          <EmptyState
            icon="📚"
            title="暂无知识库"
            description="创建您的第一个知识库，开始组织研究方向"
            action={{
              label: "创建知识库",
              onClick: handleCreate,
            }}
          />
        ) : viewMode === "card" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filtered.map((kb) => (
              <KnowledgeBaseCard
                key={kb.id}
                id={kb.id}
                name={kb.name}
                description={kb.description}
                paperCount={kb.paperCount}
                chunkCount={kb.chunkCount}
                entityCount={kb.entityCount}
                updatedAt={kb.updatedAt}
                category={kb.category}
                onEnter={() => handleEnter(kb.id)}
                onImport={() => handleImport(kb.id, kb.name)}
                onEdit={() => handleEdit(kb.name)}
                onDelete={() => handleDelete(kb.name)}
              />
            ))}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>论文数</TableHead>
                <TableHead>切片数</TableHead>
                <TableHead>实体数</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead className="w-24">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((kb) => (
                <TableRow
                  key={kb.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => handleEnter(kb.id)}
                >
                  <TableCell>
                    <div>
                      <div className="font-medium">{kb.name}</div>
                      <div className="text-sm text-muted-foreground line-clamp-1">
                        {kb.description}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>{kb.paperCount}</TableCell>
                  <TableCell>{kb.chunkCount.toLocaleString()}</TableCell>
                  <TableCell>
                    {kb.entityCount > 0 ? (
                      kb.entityCount.toLocaleString()
                    ) : (
                      <span className="text-muted-foreground/60">未构建</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{kb.updatedAt}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleEnter(kb.id)}>
                          <ArrowRight className="mr-2 h-4 w-4" />
                          进入
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleImport(kb.id, kb.name)}>
                          <Download className="mr-2 h-4 w-4" />
                          导入
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleEdit(kb.name)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          编辑
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                          <Network className="mr-2 h-4 w-4" />
                          构建图谱
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={() => handleDelete(kb.name)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          删除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Create Dialog */}
      <CreateKnowledgeBaseDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onCreate={handleCreateSubmit}
      />

      {/* Import Dialog */}
      {importTarget && (
        <ImportKnowledgeDialog
          open={!!importTarget}
          onOpenChange={(open) => {
            if (!open) setImportTarget(null);
          }}
          knowledgeBaseId={importTarget.id}
          knowledgeBaseName={importTarget.name}
        />
      )}
    </div>
  );
}
