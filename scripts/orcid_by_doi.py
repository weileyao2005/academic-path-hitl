#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DOI -> ORCID 查询（ORCID public API，stdlib only）。

用法：
    python orcid_by_doi.py 10.0000/example.2025.000001
    python orcid_by_doi.py 10.0000/example.2025.000001 10.0000/example.2025.000002
    python orcid_by_doi.py <DOI> --json

为什么用 DOI：
- Replay C 验证：两篇论文都一次命中；
- ScienceDirect 不暴露 ORCID，Crossref 的 author.orcid 常为 null；
- OpenAlex 的 authorships[].author.orcid 可能错配 / 为空。

注意：
- ORCID 的 Education 是作者自填，标 B；
- 命中后还要与姓名、单位、论文清单交叉验证。
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://pub.orcid.org/v3.0/expanded-search/"


def query_orcid(doi, timeout=30):
    q = f'digital-object-ids:"{doi}"'
    url = API + "?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "academic-path-hitl/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dois", nargs="+", help="一个或多个 DOI")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    for doi in args.dois:
        try:
            data = query_orcid(doi, args.timeout)
        except urllib.error.HTTPError as e:
            print(f"[{doi}] HTTP {e.code}: {e.reason}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[{doi}] error: {e}", file=sys.stderr)
            continue

        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            continue

        results = data.get("expanded-result") or []
        if not results:
            print(f"[{doi}] no ORCID found")
            continue
        print(f"[{doi}] found {len(results)}")
        for r in results:
            given = r.get("given-names") or ""
            family = r.get("family-names") or ""
            name = (given + " " + family).strip() or r.get("credit-name") or ""
            inst = r.get("institution-name") or []
            print(f"  ORCID: {r.get('orcid-id')}")
            if name:
                print(f"  Name: {name}")
            if inst:
                print(f"  Institutions: {'; '.join(inst)}")
            print()


if __name__ == "__main__":
    main()
