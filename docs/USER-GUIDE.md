# 归藏操作手册

## 1. 文档说明

本文档说明如何在 Windows PowerShell 中使用当前版本的归藏，包括环境检查、原料入库、AI 加工、结果校验、索引更新和常见问题处理。

当前版本已经支持：

- 通过本地对话窗口完成日常存取；
- 录入个人想法；
- 自动提取并录入普通公开网页；
- 根据关键词或记得的正文片段检索知识；
- 校验知识文件格式、引用和关联；
- 生成全库知识索引；
- 让 Codex 或 Claude Code 按项目工作流完成语义加工。

当前版本尚未支持：

- 稳定抓取需要登录、强反爬或完全依赖动态渲染的网页；
- 用单个命令自动完成单源笔记、主题回织和选题生成；
- 移动端和微信入口；
- 自动发布生成内容。

## 2. 使用前准备

### 2.1 打开项目目录

在 PowerShell 中进入项目根目录：

```powershell
Set-Location 'E:\workspace\workspace_vscode\AItools\guizang'
```

后续命令默认都在这个目录下执行。

### 2.2 检查 Python

```powershell
python --version
```

当前项目已经使用 Python 3.10.6 验证。项目只使用 Python 标准库，不需要安装额外依赖。

### 2.3 检查项目状态

```powershell
python scripts/validate.py
python scripts/rebuild_index.py --check
```

新知识库没有正式知识文件时，看到以下结果属于正常情况：

```text
校验通过：0 个知识文件。
索引检查通过：0 个知识文件。
```

### 2.4 启动可视化入口

最简单的方式是双击项目根目录中的：

```text
start-guizang.cmd
```

浏览器会自动打开：

```text
http://127.0.0.1:8765
```

也可以在 PowerShell 中运行：

```powershell
python app.py
```

启动窗口需要保持打开。结束使用时，在启动窗口按 `Ctrl+C`。

## 3. 使用对话窗口

对话框上方有三个明确模式，用于避免把搜索词误存成想法。

### 3.1 存想法

选择“存想法”，输入完整想法后按 `Enter` 或点击发送。系统会：

1. 将原文保存到 `raw/`；
2. 自动生成标题和唯一 ID；
3. 自动重建知识索引；
4. 在左侧“最近内容”中立即显示。

输入较长内容时，使用 `Shift+Enter` 换行。

### 3.2 存链接

选择“存链接”，粘贴完整的 `http://` 或 `https://` 地址后发送。系统会尝试提取标题与正文，保存成功后自动更新最近内容和索引。

抓取失败时，对话中会出现“打开原文”和“保存正文”表单。点击打开原文，在浏览器中登录并复制有权阅读的正文，填入标题和正文后点击保存。原链接会自动保留，成功后更新索引；无需重输 URL。仅返回页面标题的网页会被拒绝自动入库。

### 3.3 找知识

选择“找知识”，输入以下任一内容：

- 一个关键词，例如“内容生产”；
- 多个空格分隔的关键词，例如“知识库 选题”；
- 记得的一段原文，例如“主动生成选题”。

系统会搜索标题、标签和正文，按匹配程度返回结果。点击结果卡片即可查看完整内容。

### 3.4 查看最近内容

左侧栏显示最近更新的知识和总数量。点击任意条目即可查看全文，不需要进入文件夹查找。

## 4. 理解归藏的知识流

归藏将知识分成四层：

```text
raw 原始资料
→ notes 单源笔记
→ topics 主题知识
→ outputs 选题与创作成果
```

各目录职责：

| 目录 | 内容 | 是否由 AI 改写 |
|---|---|---|
| `raw/` | 网页正文和个人想法原文 | 否，只保存事实来源 |
| `notes/` | 对单条原料的理解和个人判断 | 是 |
| `topics/` | 多条笔记编译形成的当前结论 | 是，可持续更新 |
| `outputs/` | 从主题知识生成的选题 | 是 |
| `indexes/` | 自动生成的知识导航 | 由脚本重建 |

不要直接修改 [indexes/INDEX.md](../indexes/INDEX.md) 。它是生成文件，手工修改会在下次重建时被覆盖。

## 5. 通过命令行录入个人想法

### 5.1 短想法

```powershell
python scripts/ingest.py idea `
  --title "AI 知识库应该服务于内容生产" `
  --content "知识库的终点不应该只是回答问题，而应该主动生成选题和创作方案。"
```

成功后会输出类似结果：

```text
原始资料已写入：raw\20261105-xxxxxxxxxx-raw.md
```

### 5.2 较长的想法

先把原文保存为 UTF-8 文本文件，例如：

```text
E:\materials\idea.txt
```

然后运行：

```powershell
python scripts/ingest.py idea `
  --title "关于 AI 原生知识系统的思考" `
  --content-file 'E:\materials\idea.txt'
```

### 5.3 录入原则

- `--title` 写清楚这条想法在讨论什么；
- `--content` 必须保留原始表达，不要提前让 AI 改写；
- 相同内容当天重复录入时，系统会拒绝重复写入；
- 原始资料入库后不要直接改写正文。

## 6. 通过命令行录入网页资料

### 6.1 当前方式

当前版本不会自动抓取网页。先取得网页正文，将其保存为 UTF-8 文本文件，再执行入库。

```powershell
python scripts/ingest.py web `
  --title "文章标题" `
  --url "https://example.com/article" `
  --content-file 'E:\materials\article.txt'
```

也可以直接通过参数传入较短正文：

```powershell
python scripts/ingest.py web `
  --title "文章标题" `
  --url "https://example.com/article" `
  --content "网页原始正文"
```

### 6.2 通过 Codex 操作

对于可以公开访问的网页，推荐直接在 Codex 中输入：

```text
请把这个公开链接录入归藏：https://example.com/article

要求：
1. 获取并保存原始正文；
2. 不得补写无法获取的内容；
3. 按 schema/WORKFLOW.md 完成单源笔记、主题回织和选题生成；
4. 最后执行校验和索引重建。
```

如果网页需要登录、存在付费墙或无法读取，Codex 不应伪造正文。此时由你提供正文、文件或截图，再继续入库。

## 7. 让 AI 加工原料

入库命令只完成 `raw/` 原料保存，不会自动生成知识。

在 Codex 或 Claude Code 中使用以下指令：

```text
请检查 raw/ 中尚未加工的原始资料，按照 schema/WORKFLOW.md 完成处理。

要求：
1. 为每条原料生成带个人立场的单源笔记；
2. 优先关联已有主题，不要无意义地创建同义主题；
3. 判断新知识属于支持、补充、修正、冲突还是无关；
4. 更新受影响的主题页，并保留来源引用；
5. 基于更新后的主题知识生成可执行选题；
6. 执行结构校验和索引重建；
7. 汇报新增和修改的知识文件，以及仍然待确认的问题。
```

AI 加工规则以 [schema/WORKFLOW.md](../schema/WORKFLOW.md) 为准，字段规则以 [schema/content-schema.md](../schema/content-schema.md) 为准。

## 8. 检查 AI 生成结果

不要只看 AI 是否“写得像”。至少检查以下内容。

### 7.1 单源笔记

- 是否准确概括了原料；
- 是否区分事实、来源观点和 AI 判断；
- 是否回答“这对主人有什么用”；
- 是否明确标出无法核实的内容；
- 是否引用了对应的 `raw` ID。

### 7.2 主题页

- 是否综合多条知识，而不是简单罗列摘要；
- 是否写出当前结论；
- 是否保留冲突观点及来源；
- 是否说明新资料对原结论造成了什么变化；
- 是否保留待确认问题。

### 7.3 选题

- 是否有明确目标读者；
- 是否解决一个具体问题；
- 是否有清晰核心观点；
- 是否能追溯到主题知识和原始来源；
- 是否有进入真实创作的下一步。

不满意时，可以直接告诉 AI：

```text
这份笔记的问题是中性复述过多，没有回答“对我有什么用”。请保留事实部分，重新写“我的判断”和“可行动项”，不要修改 raw 原文。
```

## 9. 校验知识库

每次 AI 加工完成后运行：

```powershell
python scripts/validate.py
```

校验内容包括：

- frontmatter 必填字段；
- 文件目录与 `type` 是否一致；
- 时间格式；
- 网页来源地址；
- ID 是否唯一；
- 引用目标是否存在；
- `related` 是否为双向关系；
- `note → raw`、`topic → note/topic`、`brief → topic` 引用链；
- 正文是否为空。

只有看到“校验通过”才进入索引重建。

## 10. 重建与检查索引

重新生成索引：

```powershell
python scripts/rebuild_index.py
```

确认索引与当前知识文件一致：

```powershell
python scripts/rebuild_index.py --check
```

全库导航位于 [indexes/INDEX.md](../indexes/INDEX.md) 。索引按主题知识、单源笔记、选题输出和原始资料分组。

推荐每次完整加工后依次执行：

```powershell
python scripts/validate.py
python scripts/rebuild_index.py
python scripts/rebuild_index.py --check
```

## 11. 查询和使用知识

### 10.1 查找以前的知识

在 Codex 中输入：

```text
请先读取 indexes/INDEX.md，再回答：我关于“AI 原生知识库”的当前结论是什么？

要求：
1. 优先读取相关 topic；
2. 必要时下钻到 note 和 raw；
3. 区分已经确认的结论和待确认信息；
4. 列出使用到的知识文件。
```

### 10.2 生成选题

```text
请基于 topics/ 中的当前知识，为我的公众号生成 5 个选题。

每个选题需要包含：
1. 目标读者；
2. 读者问题；
3. 核心观点；
4. 可用证据；
5. 为什么现在值得写；
6. 下一步。

不要只根据单篇 raw 或 note 生成选题。
```

### 10.3 更新已有主题

```text
请处理最近新增的原料，检查它们会影响哪些已有 topic。

对每个影响说明：
- 支持；
- 补充；
- 修正；
- 冲突；
- 无关。

只更新确实受到影响的主题，保留来源和待确认项，完成后执行校验与索引重建。
```

## 12. 推荐的日常工作流

### 随手记录

```text
产生想法
→ 使用 ingest.py idea 入库
→ 暂时停在 raw 层
```

### 集中加工

```text
让 AI 检查未加工 raw
→ 生成 notes
→ 回织 topics
→ 生成 outputs
→ 人工检查
→ 校验并重建索引
```

### 内容创作

```text
从 topic 出发生成选题
→ 选择一个真实采用
→ 后续生成大纲或文章
→ 将采用与否作为反馈
```

当前建议每天随手录入，每周集中加工一次。真实使用一段时间后，再根据阻力决定是否开发自动抓取、移动端入口或周报。

## 13. 常见问题

### 12.1 `python` 命令不存在

先确认 Python 已安装并加入 `PATH`：

```powershell
py --version
```

如果 `py` 可用，可以把文档中的 `python` 替换为 `py`。

### 12.2 中文输出乱码

在当前 PowerShell 会话启用 Python UTF-8 模式：

```powershell
$env:PYTHONUTF8 = '1'
```

然后重新运行命令。

### 12.3 提示相同输入已经存在

这表示相同想法或相同网页当天已经写入。先检查 `raw/`，不要为了绕过重复保护而随意改动原文或 ID。

### 12.4 提示网页输入必须提供 HTTP(S) URL

`--url` 必须是完整地址，例如：

```text
https://example.com/article
```

不能只填写域名或本地文件路径。

### 12.5 提示引用不存在

检查 frontmatter 中的 `topics`、`related` 和 `references`：

- 是否拼错 ID；
- 目标文件是否存在；
- 是否误填了文件路径而不是 ID；
- AI 是否在创建目标文件前提前建立了引用。

### 12.6 提示关联不是双向关系

如果 A 的 `related` 中写了 B，B 的 `related` 也必须写 A。关系不确定时不要强行写入正式 `related`，先记录为待确认。

### 12.7 索引不是最新状态

运行：

```powershell
python scripts/rebuild_index.py
python scripts/rebuild_index.py --check
```

### 12.8 AI 无法读取网页

不要让 AI 猜测正文。将正文复制到 UTF-8 文本文件，再使用网页入库命令；或者直接在对话中提供正文。

## 14. 测试开发工具

普通使用不需要执行测试。修改脚本或 schema 后，应运行：

```powershell
$env:PYTHONUTF8 = '1'
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
python scripts/validate.py
python scripts/rebuild_index.py --check
```

## 15. 当前最推荐的第一次使用

准备以下两项真实内容：

1. 一个你最近确实想深入研究的个人想法；
2. 一篇与这个想法相关、你认为有价值的公开文章。

先分别录入 `raw/`，再对 Codex 说：

```text
请按照 schema/WORKFLOW.md 处理刚刚录入的两条真实资料，生成单源笔记、一个综合主题页和至少一个可执行的公众号选题。完成后执行全库校验与索引重建，并告诉我哪些判断仍然待确认。
```

这会跑通归藏当前版本最接近完整价值的使用流程。

