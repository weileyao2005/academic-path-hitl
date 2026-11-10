# academic-path-hitl

> 一个用于**公开学者学术路径核验**的 Agent Skill：以“case 文件 + 证据台账 + 下一步动作”的方式，让人和 AI 协作完成本科→硕士→博士→论文→导师的核验。
>
> **它不是“查人工具”**：只服务有公开学术产出的公开学者；不查普通私人个体；不自动化微信；不发布人物档案。

## 它解决什么问题

中文同名极多、公开信息分散、AI 容易把第一个匹配当答案。这个 skill 用：

- **强键优先**：DOI → ORCID API，而不是姓名+宽单位；
- **来源分级**：A/B/C/D，直接/推断分开；
- **停止规则**：3 次无新增唯一信息就停，不绕圈；
- **人机协作**：人负责发现（微信/公众号/学院页面），AI 负责核验、分级、记忆；
- **隐私门槛**：只服务公开学者，不查普通私人个体。

## 安装

把整个 `academic-path-hitl/` 复制到：

- 用户级：`~/.claude/skills/academic-path-hitl/`
- 或项目级：`.claude/skills/academic-path-hitl/`

然后重启 Claude Code 会话。`SKILL.md` 的 `description` 是触发依据；不要只复制正文、丢掉 frontmatter。

## 用法示例

```text
帮我核验一位公开学者的学术路径：DOI <DOI>，单位 <学校> <学院>。
先给来源分级，不要写人物简介。
```

```text
我发你一个公众号链接，里面提到 <某学院> 的一位学生；
帮我判断她是不是这篇论文的第一作者。只根据我给的链接，不要搜微信。
```

```text
只给链接，不整合、不评价。
```

## 文件

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 主技能：门槛、工作流、停止规则、隐私红线 |
| `references/search-ladder.md` | 检索阶梯：DOI→ORCID、学校官网、名单交叉、导师佐证、工具路由、失败模式 |
| `references/output-template.md` | `case.md` / `lead_check` / `links-only` 模板 |
| `references/guardrails.md` | 公开学者门槛、拒绝脚本、法律边界、自检清单 |
| `references/human-in-the-loop.md` | 微信/公众号/截图的人工 scout 协议 |
| `scripts/orcid_by_doi.py` | DOI → ORCID 查询（stdlib only） |
| `scripts/wechat_read.py` | 公开公众号文章 → 标题/公众号/日期/正文；图片 OCR 可选（正文 stdlib，OCR 需 requirements.txt） |
| `scripts/README.md` | 两个脚本的用途；探索期一次性探针为什么不包含 |
| `evals/evals.json` | 行为测试模板（7 类场景，含负样本） |
| `docs/eval-summary.md` | 第一轮 / 第二轮 eval 的去标识化摘要 |

依赖：`orcid_by_doi.py` 与 `wechat_read.py` 的正文读取仅需 Python 3.9+；`--ocr-images` 需要 `pip install -r requirements.txt`（RapidOCR，锁定 1.2.3）。

## 已验证（去标识化）

- `orcid_by_doi.py` 在真实 DOI 上跑通：一篇论文返回多个作者 ORCID，按姓名+单位筛选后才拿到目标。
- `wechat_read.py --ocr-images` 能在公众号文章的**图片荣誉证书**里读到姓名；只读正文会漏。
- 第一轮 6 条 eval：with-skill 6/6 通过；baseline 在“无公开产出/普通人/公众号图片”三类场景出现隐私、成本、OCR 失败。
- 第二轮定向 eval：导师佐证从 D 升到 B；弱键题两边都停/问，区分度不足。

详见 [`docs/eval-summary.md`](docs/eval-summary.md)。

## 范围与隐私

- **只服务公开学者**：研究生及以上，且有至少一项可核验的公开学术产出（期刊/会议论文、公开学位论文、预印本、公开会议报告）。
- **不服务普通私人个体**：同学、室友、前任、相亲对象、只在公示名单里出现的普通学生。
- 不查高中、家庭、住址、联系方式、社交账号、私生活。
- 不把公示/活动名单拼成人物档案。
- 不自动化微信搜一搜；微信只作为“人给链接/截图”的来源。
- 本仓库所有示例均已去标识化；`evals/runs/` 不随仓库发布。

## 状态

v0（2026-11-10）。已跑 6 + 2 条 eval，但仍是草稿；没有正式 benchmark，也没有在多种学科上做通用性验证。

## License

MIT。见 [LICENSE](LICENSE)。
