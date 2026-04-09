import { useState, useEffect } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Brain,
  Plus,
  Search,
  Grid,
  List as ListIcon,
  Link as LinkIcon,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { PaperListItem } from "../components/PaperListItem";
import { ImportKnowledgeDialog } from "../components/ImportKnowledgeDialog";
import { EmptyState } from "../components/EmptyState";
import { PaperTexture } from "../components/PaperTexture";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "../components/ui/breadcrumb";
import { Badge } from "../components/ui/badge";

// Mock data for papers
const MOCK_PAPERS = [
  {
    id: "paper-001",
    title: "Attention Is All You Need",
    authors: "Vaswani et al.",
    year: "2017",
    venue: "NeurIPS",
    chunkCount: 128,
    parseStatus: "completed" as const,
    entityCount: 45,
  },
  {
    id: "paper-002",
    title: "RLHF: Training Language Models to Follow Instructions",
    authors: "Ouyang et al.",
    year: "2022",
    venue: "arXiv",
    chunkCount: 96,
    parseStatus: "completed" as const,
    entityCount: 32,
  },
  {
    id: "paper-003",
    title: "Constitutional AI: Harmlessness from AI Feedback",
    authors: "Bai et al.",
    year: "2022",
    venue: "arXiv",
    chunkCount: 0,
    parseStatus: "processing" as const,
    entityCount: 0,
  },
];

const MOCK_KB = {
  id: "kb-001",
  name: "大语言模型对齐研究",
  type: "文本知识库",
};

type ViewMode = "card" | "list";

export function KnowledgeBaseDetail() {
  const navigate = useNavigate();
  const { id: _kbId } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "papers");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [showImportDialog, setShowImportDialog] = useState(false);

  // TODO: FE-04 — When real API data exceeds ~50 items, wrap this list with react-window's VariableSizeList

  // Sync tab with URL
  useEffect(() => {
    const tab = searchParams.get("tab") || "papers";
    setActiveTab(tab);
  }, [searchParams]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const handleOpenImport = (_tab?: string) => {
    setShowImportDialog(true);
  };

  const handleRead = (paperId: string) => {
    navigate(`/read/${paperId}`);
  };

  const handleNotes = (paperId: string) => {
    navigate(`/notes?paper=${paperId}`);
  };

  return (
    <div className="relative min-h-screen bg-background">
      <PaperTexture />
      {/* Breadcrumb Header */}
      <div className="magazine-toolbar sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink
                  href="/knowledge-bases"
                  className="flex items-center gap-1 cursor-pointer"
                  onClick={(e) => {
                    e.preventDefault();
                    navigate("/knowledge-bases");
                  }}
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  返回
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="font-serif flex items-center gap-2">
                  <Brain className="h-4 w-4" />
                  {MOCK_KB.name}
                </BreadcrumbPage>
              </BreadcrumbItem>
              <BreadcrumbItem>
                <Badge className="magazine-badge ml-1">
                  {MOCK_KB.type}
                </Badge>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="container-query max-w-7xl mx-auto px-6 pt-4">
        <div className="magazine-card-warm rounded-lg px-4 py-3 mt-4">
          <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="w-full max-w-2xl">
            <TabsTrigger value="papers">📄 论文列表</TabsTrigger>
            <TabsTrigger value="search">🔍 知识检索</TabsTrigger>
            <TabsTrigger value="qa">💬 知识问答</TabsTrigger>
            <TabsTrigger value="graph">🕸️ 知识图谱</TabsTrigger>
            <TabsTrigger value="compare">📊 对比分析</TabsTrigger>
          </TabsList>

          {/* 论文列表 Tab */}
          <TabsContent value="papers" className="mt-6">
            {/* Toolbar */}
            <div className="magazine-card-warm rounded-lg p-3 mb-6">
              <div className="flex items-center gap-4">
                <Button
                  onClick={() => handleOpenImport("local")}
                  className="gap-2"
                >
                  <Plus className="h-4 w-4" />
                  导入论文
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleOpenImport("url")}
                  className="gap-2"
                >
                  <LinkIcon className="h-4 w-4" />
                  从 URL 导入
                </Button>

                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="搜索论文..." className="pl-9" />
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
                    <ListIcon className="h-4 w-4" />
                    列表
                  </Button>
                </div>
              </div>
            </div>

            {/* Paper List */}
            {MOCK_PAPERS.length === 0 ? (
              <EmptyState
                icon="📚"
                title="暂无论文"
                description="导入论文开始构建您的知识库"
                action={{
                  label: "导入论文",
                  onClick: () => handleOpenImport("local"),
                }}
              />
            ) : viewMode === "list" ? (
              <motion.div className="flex flex-col gap-3" initial="hidden" animate="visible" variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }}>
                {MOCK_PAPERS.map((paper) => (
                  <motion.div key={paper.id} variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0, transition: { duration: 0.3 } } }}>
                    <PaperListItem
                      id={paper.id}
                      title={paper.title}
                      authors={paper.authors}
                      year={paper.year}
                      venue={paper.venue}
                      chunkCount={paper.chunkCount}
                      parseStatus={paper.parseStatus}
                      entityCount={paper.entityCount}
                      onRead={() => handleRead(paper.id)}
                      onNotes={() => handleNotes(paper.id)}
                    />
                  </motion.div>
                ))}
              </motion.div>
            ) : (
              <motion.div className="grid grid-cols-1 md:grid-cols-2 cq-paper-grid gap-4" initial="hidden" animate="visible" variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }}>
                {MOCK_PAPERS.map((paper) => (
                  <motion.div key={paper.id} variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0, transition: { duration: 0.3 } } }}>
                    <PaperListItem
                      id={paper.id}
                      title={paper.title}
                      authors={paper.authors}
                      year={paper.year}
                      venue={paper.venue}
                      chunkCount={paper.chunkCount}
                      parseStatus={paper.parseStatus}
                      entityCount={paper.entityCount}
                      onRead={() => handleRead(paper.id)}
                      onNotes={() => handleNotes(paper.id)}
                    />
                  </motion.div>
                ))}
              </motion.div>
            )}
          </TabsContent>

          {/* 知识检索 Tab */}
          <TabsContent value="search" className="mt-6">
            <div className="magazine-card-warm rounded-lg p-8">
              <div className="flex flex-col items-center justify-center py-8">
                <div className="w-full max-w-2xl">
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <Input
                      placeholder="输入检索问题，如：RLHF 和 DPO 方法有什么区别？"
                      className="pl-12 py-6 text-base"
                    />
                  </div>
                  <p className="text-center text-sm text-muted-foreground mt-4">
                    知识检索功能开发中 — 基于 PGVector 的跨论文语义检索
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* 知识问答 Tab */}
          <TabsContent value="qa" className="mt-6">
            <div className="magazine-card-warm rounded-lg p-8">
              <div className="flex flex-col items-center justify-center py-8">
                <div className="w-full max-w-2xl">
                  <div className="relative">
                    <Input
                      placeholder="输入您的问题..."
                      className="py-6 text-base pr-24"
                    />
                    <Button className="absolute right-2 top-1/2 -translate-y-1/2">
                      发送
                    </Button>
                  </div>
                  <p className="text-center text-sm text-muted-foreground mt-4">
                    知识问答功能开发中 — 基于知识库的 RAG 对话问答
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* 知识图谱 Tab */}
          <TabsContent value="graph" className="mt-6">
            <div className="magazine-card-warm rounded-lg p-8">
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <span className="text-5xl mb-4">🕸️</span>
                <h3 className="font-serif text-lg font-semibold text-foreground mb-2">
                  知识图谱功能开发中
                </h3>
                <p className="text-sm">
                  基于 Neo4j 的实体关系可视化，展示论文间的知识关联
                </p>
              </div>
            </div>
          </TabsContent>

          {/* 对比分析 Tab */}
          <TabsContent value="compare" className="mt-6">
            <div className="magazine-card-warm rounded-lg p-8">
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <span className="text-5xl mb-4">📊</span>
                <h3 className="font-serif text-lg font-semibold text-foreground mb-2">
                  对比分析功能开发中
                </h3>
                <p className="text-sm">
                  提取论文关键信息进行多维度对比分析
                </p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
        </div>
      </div>

      {/* Import Dialog */}
      <ImportKnowledgeDialog
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        knowledgeBaseId={MOCK_KB.id}
        knowledgeBaseName={MOCK_KB.name}
      />
    </div>
  );
}
