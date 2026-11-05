# 归藏

万象归藏，智慧自生。

归藏是一个为个人创作与 AI 产品实践服务的本地 AI 原生知识系统。它将外部资料、个人想法和实践经验持续编译成带有个人判断的知识，并进一步转化为选题与创作成果。

项目当前处于 V1 开发阶段，已经具备本地对话式入口、想法与公开链接保存、关键词和片段检索、知识文件校验及索引重建能力。

## 项目文档

- [操作手册](docs/USER-GUIDE.md) ：从原料入库到 AI 加工、校验、索引和查询的完整说明；
- [项目设计](PROJECT-DESIGN.md) ：产品定位、MVP、架构、知识编译机制和验证标准；
- [协作规范](AGENTS.md) ：目录职责、工程边界、执行纪律和项目红线；
- [项目路线图](ROADMAP.md) ：当前阶段、下一步和最近验证；
- `ai-product-thinking-20260604.md`：产品思维参考资料；
- `ai-architecture-thinking-20260610.md`：架构思维参考资料；
- `ai-tech-thinking-20260609.md`：技术选型参考资料。

## 当前目标

第一版验证以下完整闭环：

```text
输入链接或想法
→ 形成带立场的单源笔记
→ 更新已有主题知识
→ 生成可执行选题
```

## 当前能力

- 提供类似 ChatGPT 的本地对话窗口；
- 支持直接保存想法、粘贴公开链接和快速检索；
- 链接抓取失败时可直接在页面粘贴标题与正文，保留原链接并更新索引；
- 支持从最近内容或搜索结果直接查看完整知识；
- 支持在详情窗口确认删除知识；被其他知识引用时会阻止删除；
- 定义 `raw`、`note`、`topic` 和 `brief` 四类知识文件；
- 通过命令安全写入个人想法或已取得正文的网页原料；
- 校验 frontmatter、目录类型、时间、引用和双向关联；
- 根据正式知识文件生成可重建的全库索引；
- 使用 Python 标准库运行，不需要安装项目依赖。

## 使用方式

网页请求返回 HTTP 403、412、429、521 或只有标题时，会尝试使用独立无头 Edge 加载正文。此补救路径需要 `playwright` Python 包和 Microsoft Edge；不读取用户浏览器 Cookie，也不会自动处理登录或验证码。CSDN 使用文章正文区域提取，其他动态网页目前仅识别 `article` 元素。

项目根目录的 `.env` 支持配置 `DASHSCOPE_API_KEY` 和 `GUIZANG_BAILIAN_BASE_URL`，服务启动时自动读取；已有进程环境变量优先。该文件已被 Git 忽略，修改后需重启服务。

保存想法或网页后，界面会使用选择的百炼模型生成摘要，写入 `notes/` 并保留原始资料。模型输入框支持选择或直接填写模型 ID，选择保存在当前浏览器中。摘要失败时可重试，不影响已保存的原文。已有笔记不会被自动覆盖。

启动前在服务进程的环境中配置 `DASHSCOPE_API_KEY`；不会读取或复用其他服务的密钥。默认使用百炼北京兼容地址，可通过 `GUIZANG_BAILIAN_BASE_URL` 指定控制台提供的完整兼容接口地址（以 `/v1` 结尾）。密钥对应地域必须与地址一致。生成摘要会将该条原文发送到所配置的百炼接口，并产生相应模型费用。当前单条原文上限为 60000 字符。

完整使用说明见 [操作手册](docs/USER-GUIDE.md) 。以下为最小命令速查。

推荐直接双击项目根目录下的 `start-guizang.cmd`。浏览器会自动打开：

```text
http://127.0.0.1:8765
```

也可以在 PowerShell 中启动：

```powershell
python app.py
```

服务启动时会自动停止上一次由归藏记录的本地服务进程，避免重复启动占用端口。

以下命令行方式作为备用入口保留。

录入一条个人想法：

```powershell
python scripts/ingest.py idea --title "想法标题" --content "想法原文"
```

录入一篇已经保存为 UTF-8 文本的网页正文：

```powershell
python scripts/ingest.py web --title "文章标题" --url "https://example.com/article" --content-file "E:\path\article.txt"
```

入库命令只写入不可伪造的原始资料，不负责生成 AI 笔记。随后复制 [schema/templates](schema/templates) 中的对应模板，按照 [AI 工作流](schema/WORKFLOW.md) 完成语义加工，并运行：

```powershell
python scripts/validate.py
python scripts/rebuild_index.py
python scripts/rebuild_index.py --check
```

运行自动化测试：

```powershell
python -m unittest discover -s tests -v
```

本地界面能够抓取普通公开网页；需要登录、强反爬或动态渲染的页面可能无法读取。当前尚未实现主题回织的自动编排。

