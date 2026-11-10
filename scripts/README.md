# scripts

| 文件 | 用途 | 依赖 |
|---|---|---|
| `orcid_by_doi.py` | DOI → ORCID（ORCID public API） | 仅 stdlib |
| `wechat_read.py` | 公开公众号文章 → 标题/公众号/日期/正文；`--ocr-images` 读图片文字 | 正文读取仅 stdlib；图片 OCR 需要 `pip install -r requirements.txt` |

## 为什么只有这两个

- 它们是 skill 的**可复用运行依赖**：一个把论文 DOI 变成 ORCID，一个把公众号文章变成可读文本/图片 OCR。
- 探索期的一次性脚本（Crossref/OpenAlex/CNKI 探针、屏幕控件树 dump、微信 live 自动化）**没有放进仓库**：
  - 有些是临时探针，不是 skill 的运行依赖；
  - 有些含真实姓名/查询/私人数据，不适合公开；
  - 微信搜一搜自动化已暂停，不应作为公开功能发布。

如果你要复现整条流水线，建议用公开 API（Crossref/OpenAlex/ORCID/PubMed）+ 本仓库的两个脚本，自己写参数化的探针；不要提交真实人物数据。
