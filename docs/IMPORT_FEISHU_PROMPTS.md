# 从飞书文档导入提示词

## 说明

由于无法直接访问飞书文档的完整文本内容，我已经根据文档目录结构创建了提示词条目的框架。要完整迁移所有提示词内容，请按照以下步骤操作：

## 方法一：使用导入脚本（推荐）

1. **从飞书文档复制内容**
   - 打开文档：https://superhuang.feishu.cn/wiki/W1LCwYA8eiTl77kpi81c31yNnJd
   - 复制所有提示词内容到一个文本文件（`.txt` 或 `.md` 格式）

2. **运行导入脚本**
   ```bash
   python scripts/add_feishu_prompts.py <文本文件路径>
   ```

   示例：
   ```bash
   python scripts/add_feishu_prompts.py prompts_from_feishu.txt
   ```

3. **脚本会自动**
   - 解析文本内容
   - 提取所有提示词章节
   - 添加到 `data/prompts/prompts.json` 文件中
   - 自动生成ID、标识符、标签等

## 方法二：手动添加

如果导入脚本无法正确解析文档格式，您可以：

1. 打开 `data/prompts/prompts.json` 文件
2. 找到需要补充内容的提示词条目（已创建框架，content字段需要补充）
3. 从飞书文档复制对应的完整提示词内容
4. 替换 `content` 字段中的占位符文本

## 已创建的提示词条目

根据文档目录结构，以下提示词条目已创建（ID 7-19）：

- 06 必备的Windsurf技巧
- 使用AI IDE进行创作
- 改写提示词
- 使用提示词生成精美图片
- 最终版本的提示词
- 图片字幕生成器
- 使用Deepseek R1，帮老外起中文名吧！
- 设置WorkSpace AI Rules
- 做一档你自己的AI播客
- 做一个你专属的好文推荐网站（DeepSeek R1 + 飞书多维表格）
- 一键批量提取抖音博主视频：文案提取+风格分析+文案改写
- DeepSeek驱动的网页金句卡片生成
- 开发浏览器插件

**注意**：这些条目目前只有框架和占位符内容，需要从飞书文档中复制完整的提示词文本进行填充。

## 提示词结构

每个提示词条目包含以下字段：

```json
{
  "name": "提示词名称",
  "description": "简要描述",
  "category": "代码",
  "tags": ["标签1", "标签2"],
  "author": "",
  "url": "https://superhuang.feishu.cn/wiki/W1LCwYA8eiTl77kpi81c31yNnJd",
  "content": "完整的提示词内容",
  "view_count": 0,
  "created_at": "2025-12-01T00:00:00Z",
  "is_featured": false,
  "id": 7,
  "identifier": "prompt-identifier"
}
```

## 验证

添加完成后，可以通过以下方式验证：

1. 检查JSON格式是否正确：
   ```bash
   python -m json.tool data/prompts/prompts.json > /dev/null
   ```

2. 启动服务器，访问 `/prompts` 页面查看所有提示词

3. 检查提示词内容是否完整显示

## 注意事项

- 确保 `content` 字段包含完整的提示词文本
- 保持JSON格式的正确性
- 每个提示词的 `id` 必须唯一
- `identifier` 会自动生成，但应确保唯一性

