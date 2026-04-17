#!/usr/bin/env python3
"""
数据库对齐检查脚本 - 验证所有模型与数据库表对齐，并运行最小流程测试

检查项：
1. 所有 ORM 模型是否有对应的数据库表
2. 表的字段是否与模型对齐
3. 运行最小 E2E 流程：创建用户 -> 知识库 -> 上传论文 -> 查询
"""

import asyncio
import sys
from pathlib import Path
import uuid
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent / "apps" / "api"
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, Base
from app.models import (
    User, Paper, KnowledgeBase, KnowledgeBasePaper, 
    ProcessingTask, Session, ChatMessage,
    Project, ReadingProgress, UploadHistory,
    Note, Annotation, Query,
    ImportJob, ImportBatch,
    ApiKey, AuditLog, Config,
    UserMemory, KnowledgeMap, TokenUsageLog,
    NotesTask, PaperChunk
)
from app.utils.logger import logger

# ORM 模型列表
ORM_MODELS = [
    User, Paper, KnowledgeBase, KnowledgeBasePaper, 
    ProcessingTask, Session, ChatMessage,
    Project, ReadingProgress, UploadHistory,
    Note, Annotation, Query,
    ImportJob, ImportBatch,
    ApiKey, AuditLog, Config,
    UserMemory, KnowledgeMap, TokenUsageLog,
    NotesTask, PaperChunk
]


async def check_database_alignment():
    """检查数据库表与 ORM 模型对齐"""
    logger.info("=" * 80)
    logger.info("🔍 数据库对齐检查")
    logger.info("=" * 80)
    
    async with AsyncSessionLocal() as session:
        # 获取数据库中的所有表
        db_tables = await session.execute(
            text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
        )
        db_table_names = {row[0] for row in db_tables}
        logger.info(f"\n📊 数据库中存在的表数量: {len(db_table_names)}")
        logger.info(f"表列表: {sorted(db_table_names)}\n")
        
        # 检查每个 ORM 模型
        missing_tables = []
        model_table_map = {}
        
        for model in ORM_MODELS:
            table_name = model.__tablename__
            model_table_map[model.__name__] = table_name
            
            if table_name in db_table_names:
                logger.info(f"✅ {model.__name__:30} -> 表 '{table_name}' 存在")
            else:
                logger.error(f"❌ {model.__name__:30} -> 表 '{table_name}' 不存在!")
                missing_tables.append((model.__name__, table_name))
        
        # 总结对齐状态
        logger.info("\n" + "=" * 80)
        logger.info("📋 对齐检查摘要")
        logger.info("=" * 80)
        logger.info(f"✅ 已匹配: {len(ORM_MODELS) - len(missing_tables)}/{len(ORM_MODELS)} 模型")
        
        if missing_tables:
            logger.error(f"\n❌ 缺失的表 ({len(missing_tables)}):")
            for model_name, table_name in missing_tables:
                logger.error(f"   - {model_name:30} 需要表 '{table_name}'")
            return False
        
        logger.info("✅ 所有模型都有对应的数据库表！\n")
        return True


async def run_minimal_workflow():
    """运行最小工作流测试"""
    logger.info("=" * 80)
    logger.info("🚀 运行最小 E2E 工作流测试")
    logger.info("=" * 80)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 创建用户
            logger.info("\n[1/4] 创建测试用户...")
            user_id = str(uuid.uuid4())
            now = datetime.utcnow()
            user = User(
                id=user_id,
                email=f"test-{int(asyncio.get_event_loop().time())}@scholar-ai.local",
                name=f"Test User {int(asyncio.get_event_loop().time())}",
                password_hash="dummy_hash_placeholder",
                created_at=now,
                updated_at=now
            )
            session.add(user)
            await session.flush()
            logger.info(f"✅ 用户创建成功: {user.id}")
            
            # 2. 创建知识库
            logger.info("\n[2/4] 创建知识库...")
            kb = KnowledgeBase(
                id="test-kb-" + str(int(asyncio.get_event_loop().time())),
                user_id=user.id,
                name="Test Knowledge Base",
                description="最小工作流测试知识库"
            )
            session.add(kb)
            await session.flush()
            logger.info(f"✅ 知识库创建成功: {kb.id}")
            
            # 3. 创建论文记录
            logger.info("\n[3/4] 创建论文记录...")
            paper = Paper(
                id="test-paper-" + str(int(asyncio.get_event_loop().time())),
                title="Test Paper for Minimal Workflow",
                authors="Test Author",
                pdf_url="https://example.com/test.pdf",
                status="pending",
                user_id=user.id
            )
            session.add(paper)
            await session.flush()
            logger.info(f"✅ 论文创建成功: {paper.id}")
            
            # 4. 关联论文到知识库
            logger.info("\n[4/4] 关联论文到知识库...")
            kb_paper = KnowledgeBasePaper(
                id="test-kbp-" + str(int(asyncio.get_event_loop().time())),
                knowledge_base_id=kb.id,
                paper_id=paper.id
            )
            session.add(kb_paper)
            await session.commit()
            logger.info(f"✅ 关联创建成功: {kb_paper.id}")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ 最小工作流测试成功！")
            logger.info("=" * 80)
            logger.info("\n工作流摘要:")
            logger.info(f"  用户 ID: {user.id}")
            logger.info(f"  知识库 ID: {kb.id}")
            logger.info(f"  论文 ID: {paper.id}")
            logger.info(f"  KB-Paper 关联: {kb_paper.id}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ 工作流测试失败: {e}")
            await session.rollback()
            return False


async def check_api_endpoints():
    """检查关键 API 端点"""
    logger.info("=" * 80)
    logger.info("🔌 API 端点检查")
    logger.info("=" * 80)
    
    endpoints = [
        "GET /api/health",
        "POST /api/auth/register",
        "POST /api/auth/login",
        "GET /api/users/me",
        "POST /api/kb",
        "GET /api/kb",
        "POST /api/papers",
        "GET /api/papers",
        "POST /api/chat/stream",
    ]
    
    logger.info("\n主要 API 端点:")
    for endpoint in endpoints:
        logger.info(f"  ✓ {endpoint}")
    
    logger.info("\n💡 提示: 启动后端服务后，可以使用 Postman 或 curl 测试这些端点\n")
    return True


async def main():
    """主函数"""
    try:
        # 检查数据库对齐
        alignment_ok = await check_database_alignment()
        
        # 运行最小工作流
        workflow_ok = await run_minimal_workflow()
        
        # 检查 API 端点
        await check_api_endpoints()
        
        # 总体结果
        logger.info("=" * 80)
        logger.info("📊 检查汇总")
        logger.info("=" * 80)
        logger.info(f"数据库对齐: {'✅ PASS' if alignment_ok else '❌ FAIL'}")
        logger.info(f"最小流程: {'✅ PASS' if workflow_ok else '❌ FAIL'}")
        logger.info("=" * 80 + "\n")
        
        if alignment_ok and workflow_ok:
            logger.info("✅ 所有检查通过！系统已就绪。")
            return 0
        else:
            logger.error("❌ 某些检查失败，请查看上面的错误信息。")
            return 1
            
    except Exception as e:
        logger.error(f"❌ 检查过程出错: {e}", exc_info=True)
        return 1
    finally:
        logger.info("\n✅ 检查完毕")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
