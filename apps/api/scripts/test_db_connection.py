"""
数据库连接测试脚本

测试数据库连接:
- PostgreSQL
- Neo4j
- Redis

使用方法:
    cd apps/api
    python -m scripts.test_db_connection

或者:
    python scripts/test_db_connection.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import (
    postgres_db,
    neo4j_db,
    redis_db,
    init_databases,
    close_databases,
)
from app.utils.logger import logger


async def test_postgres():
    """测试 PostgreSQL 连接"""
    print("\n🐘 测试 PostgreSQL 连接...")
    print(
        f"   连接地址: {settings.DATABASE_URL.replace(settings.DATABASE_URL.split('@')[0].split(':')[-1], '***')}"
    )

    try:
        await postgres_db.connect()

        # 测试查询
        result = await postgres_db.fetchrow("SELECT version()")
        print(f"   ✅ PostgreSQL 连接成功!")
        print(f"   📊 服务器版本: {result['version'][:50]}...")

        # 测试创建表
        await postgres_db.execute("""
            CREATE TABLE IF NOT EXISTS test_connection (
                id SERIAL PRIMARY KEY,
                test_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 插入测试数据
        await postgres_db.execute(
            "INSERT INTO test_connection (test_data) VALUES ($1)",
            "Connection test from local dev",
        )

        # 查询测试数据
        rows = await postgres_db.fetch(
            "SELECT * FROM test_connection ORDER BY created_at DESC LIMIT 1"
        )
        print(f"   📄 测试数据写入成功: {rows[0]['test_data']}")

        # 清理测试表
        await postgres_db.execute("DROP TABLE IF EXISTS test_connection")
        print("   🧹 测试表已清理")

        return True
    except Exception as e:
        print(f"   ❌ PostgreSQL 连接失败: {e}")
        return False


async def test_neo4j():
    """测试 Neo4j 连接"""
    print("\n🕸️  测试 Neo4j 连接...")
    print(f"   连接地址: {settings.NEO4J_URI}")
    print(f"   用户名: {settings.NEO4J_USER}")

    try:
        await neo4j_db.connect()

        # 测试创建节点
        result = await neo4j_db.run(
            "CREATE (t:Test {message: $msg, timestamp: datetime()}) RETURN t",
            {"msg": "Connection test from local dev"},
        )
        print(f"   ✅ Neo4j 连接成功!")
        print(f"   📄 测试节点创建成功")

        # 查询测试节点
        result = await neo4j_db.run(
            "MATCH (t:Test) RETURN t.message as msg ORDER BY t.timestamp DESC LIMIT 1"
        )
        print(f"   📄 查询结果: {result[0]['msg'] if result else 'None'}")

        # 清理测试节点
        await neo4j_db.run("MATCH (t:Test) DELETE t")
        print("   🧹 测试节点已清理")

        return True
    except Exception as e:
        print(f"   ❌ Neo4j 连接失败: {e}")
        return False


async def test_redis():
    """测试 Redis 连接"""
    print("\n⚡ 测试 Redis 连接...")
    print(f"   连接地址: {settings.REDIS_URL}")

    try:
        await redis_db.connect()

        # 测试写入
        test_key = "test:connection"
        test_value = "Connection test from local dev"
        await redis_db.set(test_key, test_value, expire=60)

        # 测试读取
        result = await redis_db.get(test_key)
        print(f"   ✅ Redis 连接成功!")
        print(f"   📄 写入/读取测试: {result}")

        # 清理
        await redis_db.delete(test_key)
        print("   🧹 测试键已清理")

        return True
    except Exception as e:
        print(f"   ❌ Redis 连接失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 ScholarAI 数据库连接测试")
    print("=" * 60)
    print(
        f"\n📍 服务器: {settings.DATABASE_URL.split('@')[1].split(':')[0] if '@' in settings.DATABASE_URL else 'localhost'}"
    )
    print("📦 测试服务: PostgreSQL | Neo4j | Redis")

    results = {}

    try:
        # 测试 PostgreSQL
        results["postgresql"] = await test_postgres()

        # 测试 Neo4j
        results["neo4j"] = await test_neo4j()

        # 测试 Redis
        results["redis"] = await test_redis()

    finally:
        # 关闭所有连接
        print("\n🔌 关闭数据库连接...")
        await close_databases()

    # 打印测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    for service, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {service.upper():12} {status}")

    all_passed = all(results.values())
    print("=" * 60)

    if all_passed:
        print("🎉 所有数据库连接测试通过!")
        print("\n💡 现在你可以启动后端服务:")
        print("   uvicorn app.main:app --reload --port 8000")
        return 0
    else:
        print("⚠️ 部分数据库连接失败，请检查:")
        print("   1. 数据库服务是否运行")
        print("   2. .env.local 中的密码是否正确")
        print("   3. 本地网络是否可以访问数据库服务器")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
