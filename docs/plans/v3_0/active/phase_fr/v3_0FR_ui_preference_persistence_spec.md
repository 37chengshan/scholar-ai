# v3.0FR UI Preference Persistence Spec

## 1. 目的

把真正属于“界面偏好”的状态从页面本地 `useState` 中拆出，避免刷新、切页和回到工作台后丢失上下文。

## 2. Read 偏好状态

建议进入持久化 store 的字段：

1. `rightTab`
2. `isPanelOpen`
3. `isFullscreen`
4. `panelWidth`

不进入偏好 store 的字段：

1. `currentPage`
2. `annotations`
3. `linkedNoteContent`
4. `noteSaveStatus`

原因：这些字段属于运行时数据，不是用户的布局或展示偏好。

## 3. Notes 偏好状态

建议进入持久化 store 的字段：

1. `selectedFolderId`
2. `tagFilter`

不进入偏好 store 的字段：

1. `selectedNoteId`
2. `editorContent`
3. `deleteNoteId`

原因：这些字段与当前工作对象和实时编辑内容强绑定，误持久化会造成恢复语义污染。

## 4. 存储约束

1. 使用现有 `zustand` + `persist` 模式。
2. 只存可 JSON 序列化字段。
3. 浏览器环境缺失时必须安全降级。