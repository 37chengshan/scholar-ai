FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制构建产物
COPY dist ./dist
COPY prisma ./prisma

# 生成Prisma客户端
RUN npx prisma generate

EXPOSE 4000

CMD ["node", "dist/index.js"]
