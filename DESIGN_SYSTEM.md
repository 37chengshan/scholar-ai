# ScholarAI 设计系统规则

> 本项目设计系统基于 React + TypeScript + Tailwind CSS + Framer Motion

---

## 1. 设计令牌 (Design Tokens)

### 颜色系统

```css
/* CSS Variables - 定义于 globals.css */
--bg-primary: #050508      /* 主背景色 */
--bg-secondary: #0a0a0f    /* 次级背景 */
--bg-tertiary: #12121a     /* 第三层背景 */
--bg-elevated: #1a1a25     /* 浮层背景 */
--neon-cyan: #00f5ff       /* 霓虹青 - 主强调色 */
--neon-blue: #0080ff       /* 霓虹蓝 */
--neon-purple: #b829dd     /* 霓虹紫 */
--neon-pink: #ff0080       /* 霓虹粉 */
```

### 字体系统

- **主字体**: `'Sora', sans-serif`
- **显示字体**: `font-display` (Sora)
- **字号比例**: 使用 Tailwind 默认比例

### 间距系统

- 使用 Tailwind 默认间距 (4px 基准)
- 常用间距: `px-4 sm:px-6 lg:px-8` (容器内边距)

---

## 2. 组件架构

### Button 组件

位置: `src/components/ui/Button.tsx`

```typescript
// 变体
variant: 'primary' | 'secondary' | 'ghost' | 'neon'

// 尺寸
size: 'sm' | 'md' | 'lg'

// 样式特征
- Primary: 渐变背景 cyan -> blue, 霓虹发光效果
- Secondary: 半透明背景 + 边框
- Ghost: 边框 + 青色文字
- Neon: 纯青色背景 + 黑色文字
```

### Navigation 组件

位置: `src/components/ui/Navigation.tsx`

```typescript
// 特性
- 固定顶部导航
- Glassmorphism 效果 (滚动后)
- 移动端侧边栏菜单
- 平滑滚动锚点
```

---

## 3. 样式工具类

### Glassmorphism (玻璃拟态)

```css
.glass {
  background: rgba(18, 18, 26, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-strong {
  background: rgba(26, 26, 37, 0.85);
  backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

### 文字渐变

```css
.text-gradient {
  background-image: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

### 发光效果

```css
.glow-cyan {
  box-shadow: 0 0 20px rgba(0, 245, 255, 0.5);
}

.border-glow {
  border: 1px solid rgba(0, 245, 255, 0.3);
  box-shadow: 0 0 10px rgba(0, 245, 255, 0.1),
              inset 0 0 10px rgba(0, 245, 255, 0.05);
}
```

---

## 4. 动画系统

### Framer Motion 模式

```typescript
// 按钮悬停
<motion.button
  whileHover={{ scale: 1.02 }}
  whileTap={{ scale: 0.98 }}
>

// 淡入动画
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5, delay: 0.2 }}
>

// 导航栏隐藏/显示
<motion.nav
  animate={{ y: navHidden ? -100 : 0 }}
  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
>
```

---

## 5. 图标系统

- **图标库**: `lucide-react`
- **使用方式**: 直接导入需要的图标
- **常用图标**: BookOpen, Menu, X, Settings, Library, etc.

```typescript
import { BookOpen, Menu } from 'lucide-react';
<BookOpen className="w-4 h-4 text-white" />
```

---

## 6. 响应式断点

基于 Tailwind 默认断点:

- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

常用模式: `hidden lg:flex` (桌面显示，移动端隐藏)

---

## 7. Figma 设计转代码指南

### 从 Figma 到 React 组件

1. **颜色映射**:
   - Figma 主色 -> CSS Variable 或 Tailwind 类
   - 深色背景 -> `bg-bg-primary`, `bg-bg-secondary`
   - 霓虹强调色 -> `text-neon-cyan`, `bg-neon-cyan`

2. **间距映射**:
   - Figma 8px -> Tailwind `2` (0.5rem)
   - Figma 16px -> Tailwind `4` (1rem)
   - Figma 24px -> Tailwind `6` (1.5rem)

3. **圆角映射**:
   - Figma 8px -> `rounded-lg`
   - Figma 16px -> `rounded-2xl`

4. **阴影映射**:
   - Figma 模糊效果 -> `backdrop-blur-xl`
   - Figma 发光 -> 自定义 `glow-*` 类

5. **文字样式**:
   - 标题 -> `font-display font-bold`
   - 正文 -> 默认 sans
   - 大写 + 字间距 -> `uppercase tracking-wider`

---

## 8. 新组件创建模板

```typescript
import React from 'react';
import { motion } from 'framer-motion';

interface ComponentNameProps {
  // props 定义
}

export const ComponentName: React.FC<ComponentNameProps> = ({
  // props 解构
}) => {
  return (
    <motion.div
      className="glass rounded-xl p-6"
      // animation props
    >
      {/* 内容 */}
    </motion.div>
  );
};
```

---

## 9. 关键文件位置

| 用途 | 文件路径 |
|------|----------|
| 全局样式 | `src/styles/globals.css` |
| 按钮组件 | `src/components/ui/Button.tsx` |
| 导航组件 | `src/components/ui/Navigation.tsx` |
| Tailwind 配置 | `tailwind.config.js` |
| 主入口 | `src/main.tsx` |
| 路由配置 | `src/App.tsx` |

---

## 10. 设计原则

1. **深色优先**: 所有组件默认支持深色主题
2. **霓虹强调**: 使用 cyan/blue/purple 渐变和发光效果
3. **玻璃拟态**: 浮层使用 glass/glass-strong 类
4. **动效增强**: 所有交互元素添加 Framer Motion 动画
5. **响应式**: 移动端优先设计，渐进增强
6. **无障碍**: 支持 `prefers-reduced-motion`
