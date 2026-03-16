import React from 'react';
import { Helmet } from 'react-helmet-async';

export const LandingSEO: React.FC = () => {
  const siteUrl = typeof window !== 'undefined' ? window.location.origin : 'https://scholar-ai.example.com';

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'ScholarAI 智读',
    applicationCategory: 'ResearchApplication',
    description: 'AI-powered academic paper reading assistant with Agentic RAG',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'CNY',
    },
    featureList: [
      '智能论文搜索',
      'AI 论文精读',
      '知识图谱构建',
      '文献库智能检索',
    ],
    author: {
      '@type': 'Organization',
      name: 'ScholarAI Team',
    },
  };

  return (
    <Helmet>
      {/* Basic Meta Tags */}
      <title>ScholarAI 智读 - AI论文精读助手 | 构建个人知识库，秒级文献检索</title>
      <meta
        name="description"
        content="ScholarAI智读是基于Agentic RAG的智能学术阅读平台。上传PDF自动生成结构化笔记，支持跨文档语义检索，构建个人知识图谱。让科研人员从'读完一篇论文需要3小时'缩短到'掌握核心内容只需10分钟'。"
      />
      <meta name="keywords" content="AI论文阅读, 文献库管理, 智能检索, Agentic RAG, 知识图谱, 学术工具" />
      <meta name="author" content="ScholarAI Team" />
      <meta name="robots" content="index, follow" />
      <link rel="canonical" href={siteUrl} />

      {/* Open Graph / Facebook */}
      <meta property="og:type" content="website" />
      <meta property="og:url" content={siteUrl} />
      <meta property="og:title" content="ScholarAI 智读 - AI论文精读助手" />
      <meta
        property="og:description"
        content="让科研人员从'读完一篇论文需要3小时'缩短到'掌握核心内容只需10分钟'"
      />
      <meta property="og:site_name" content="ScholarAI 智读" />
      <meta property="og:locale" content="zh_CN" />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content="ScholarAI 智读 - AI论文精读助手" />
      <meta
        name="twitter:description"
        content="让科研人员从'读完一篇论文需要3小时'缩短到'掌握核心内容只需10分钟'"
      />

      {/* JSON-LD Structured Data */}
      <script type="application/ld+json">
        {JSON.stringify(jsonLd)}
      </script>
    </Helmet>
  );
};
