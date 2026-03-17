// setup-env.js - 在 TypeScript 编译和模块加载之前执行
// 确保 OSS_ENDPOINT 在 storage.ts 模块加载前设置
process.env.OSS_ENDPOINT = process.env.OSS_ENDPOINT || 'local';
process.env.LOCAL_STORAGE_PATH = process.env.LOCAL_STORAGE_PATH || '/Users/cc/sc/scholar-ai/backend-node/uploads';
