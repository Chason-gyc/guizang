# 归藏知识文件规范

## 适用范围

`raw/`、`notes/`、`topics/` 和 `outputs/` 下的正式 Markdown 文件必须使用本文定义的 frontmatter。`indexes/` 是可重建产物，不使用本规范。

V1 使用 YAML 的一个受限子集：字段名固定，字符串使用双引号，集合使用 JSON 风格数组。这样可以只用 Python 标准库完成确定性解析和校验。

## 通用字段

```yaml
---
id: "20261105-example"
title: "示例标题"
type: "raw"
status: "active"
created_at: "2026-11-05 10:00"
updated_at: "2026-11-05 10:00"
source_url: ""
source_type: "idea"
tags: ["AI", "知识管理"]
topics: []
related: []
references: []
---
```

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | 字符串 | 全库唯一，只能包含小写英文字母、数字和连字符 |
| `title` | 字符串 | 非空自然语言标题 |
| `type` | 字符串 | `raw`、`note`、`topic` 或 `brief` |
| `status` | 字符串 | `active`、`pending` 或 `archived` |
| `created_at` | 字符串 | 北京时间 `YYYY-MM-DD HH:mm` |
| `updated_at` | 字符串 | 北京时间 `YYYY-MM-DD HH:mm`，不得早于创建时间 |
| `source_url` | 字符串 | `source_type` 为 `web` 时必须是 HTTP(S) URL |
| `source_type` | 字符串 | `web` 或 `idea` |
| `tags` | 字符串数组 | 语义标签，允许为空 |
| `topics` | ID 数组 | 指向相关 `topic` 文件，允许为空 |
| `related` | ID 数组 | 知识关联，正式关系必须双向 |
| `references` | ID 数组 | 当前内容依据的上游知识 ID |

## 分层约束

- `raw/` 只能使用 `type: "raw"`，允许 `references` 为空；
- `notes/` 只能使用 `type: "note"`，必须至少引用一个 `raw`；
- `topics/` 只能使用 `type: "topic"`，必须至少引用一个 `note` 或其他 `topic`；
- `outputs/` 只能使用 `type: "brief"`，必须至少引用一个 `topic`；
- `topics`、`related` 和 `references` 中出现的 ID 必须真实存在；
- `related` 关系必须在目标文件中反向出现；
- 正文不能为空。

## 目录与类型映射

| 目录 | 类型 |
|---|---|
| `raw/` | `raw` |
| `notes/` | `note` |
| `topics/` | `topic` |
| `outputs/` | `brief` |

## 校验

在项目根目录运行：

```powershell
python scripts/validate.py
```

任何校验错误都会返回非零退出码，正式知识文件不得在校验失败时进入后续索引或编译流程。

