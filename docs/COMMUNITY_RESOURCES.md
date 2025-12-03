# 社区资源抓取说明

## 概述

社区资源页面 `/resources` 显示来自 [devmaster.cn](http://devmaster.cn/resource/AICoding%E7%A4%BE%E5%8C%BA) 的资源链接。

## 资源分类

社区资源按以下分类组织：
- **飞书知识库**：飞书文档和知识库资源
- **技术社区**：技术社区和论坛资源
- **Cursor资源**：Cursor相关的社区资源
- **其他**：其他类型的资源

### 飞书知识库

1. **AGI之路 - AI Code专区**
   - URL: https://waytoagi.feishu.cn/wiki/Pxj8wsMmOii7ZSkN0mYc8xdtnHb
   - 描述: AGI之路飞书知识库中的AI编程相关内容专区

2. **黄叔AI编程蓝皮书**
   - 需要更新实际URL
   - 描述: 黄叔AI编程蓝皮书 - 飞书知识库中的AI编程系列内容

3. **LangGPT社区 - AI编程系列**
   - 需要更新实际URL
   - 描述: LangGPT社区中的AI编程系列内容

4. **AIGC创意猎人 - AI编程专区**
   - 需要更新实际URL
   - 描述: AIGC创意猎人飞书知识库中的AI编程专区

5. **玩转AI实验室 - AI编程专区**
   - 需要更新实际URL
   - 描述: 玩转AI实验室飞书知识库中的AI编程专区

### 技术社区

1. **掘金 AI编程**
   - URL: https://juejin.cn/tag/AI%E7%BC%96%E7%A8%8B
   - 描述: 掘金技术社区中的AI编程相关内容

2. **CSDN AI编程**
   - URL: https://blog.csdn.net/nav/python
   - 描述: CSDN技术社区中的AI编程相关内容

## 自动抓取脚本

使用 `scripts/crawl_devmaster_resources.py` 脚本可以自动从 devmaster.cn 抓取最新的社区资源。

### 使用方法

```bash
python scripts/crawl_devmaster_resources.py
```

### 脚本功能

- 自动访问 devmaster.cn 的资源页面
- 解析页面HTML，提取所有资源链接
- 自动分类（飞书知识库/技术社区）
- 检查重复，避免重复添加
- 自动生成标识符和ID
- 更新 resources.json 文件

### 注意事项

1. 脚本需要安装 `beautifulsoup4` 和 `httpx`
2. 如果某些链接是占位符，需要手动更新实际URL
3. 脚本会自动跳过已存在的资源（根据URL判断）

## 手动更新资源

如果自动抓取脚本无法正常工作，可以手动编辑 `data/resources.json` 文件：

1. 找到需要更新的资源条目
2. 更新 `url` 字段为实际链接
3. 更新 `description` 字段为更详细的描述（可选）
4. 保存文件

## 数据结构

每个资源条目包含以下字段：

```json
{
  "title": "资源标题",
  "description": "资源描述",
  "type": "知识库/社区",
  "category": "飞书知识库/技术社区",
  "tags": ["标签1", "标签2"],
  "url": "资源链接",
  "author": "作者/来源",
  "view_count": 0,
  "created_at": "2025-12-01T00:00:00Z",
  "is_featured": false,
  "id": 6,
  "identifier": "resource-identifier"
}
```

## 更新频率

建议定期（如每周或每月）运行抓取脚本，以确保资源列表是最新的。

