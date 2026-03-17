// tests/setup.ts
/// <reference types="jest" />

// 必须在任何其他导入之前加载环境变量
process.env.OSS_ENDPOINT = 'local'; // 强制使用本地存储
require('dotenv').config({ path: '.env.test' });

// 设置测试环境
process.env.NODE_ENV = 'test';
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || 'test-access-secret';
process.env.JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'test-refresh-secret';

// 清除可能存在的全局 Prisma 实例，强制重新连接
if (global.prisma) {
  global.prisma.$disconnect().catch(() => {});
  global.prisma = undefined;
}

// 清除 require 缓存，强制重新加载数据库模块
delete require.cache[require.resolve('../src/config/database')];

// 全局测试超时（10 秒）
jest.setTimeout(10000);

// 测试结束后清理
afterAll(async () => {
  if (global.prisma) {
    await global.prisma.$disconnect();
  }
});
