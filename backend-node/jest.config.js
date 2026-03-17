/** @type {import('jest').Config} */

// 在 Jest 启动时立即设置测试环境变量
process.env.OSS_ENDPOINT = 'local'; // 必须在任何模块加载前设置
process.env.LOCAL_STORAGE_PATH = '/Users/cc/sc/scholar-ai/backend-node/uploads'; // 必须在任何模块加载前设置
require('dotenv').config({ path: '.env.test' });
process.env.NODE_ENV = 'test';

module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/*.test.ts', '**/*.spec.ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  moduleFileExtensions: ['ts', 'js', 'json'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/index.ts',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFiles: ['<rootDir>/tests/setup-env.js'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  verbose: true,
  clearMocks: true,
  restoreMocks: true,
};
