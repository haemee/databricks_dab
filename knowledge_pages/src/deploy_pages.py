# Databricks notebook source
# MAGIC %md
# MAGIC # Knowledge Pages 배포
# MAGIC
# MAGIC `knowledge_pages.json`의 페이지를 대상 도메인에 생성하거나 업데이트합니다.
# MAGIC 같은 제목의 페이지가 이미 있으면 업데이트하고, 없으면 새로 만듭니다.

# COMMAND ----------

dbutils.widgets.text("config_path", "")
dbutils.widgets.text("target_domain", "", "대상 도메인 ID (domains/... 형태)")
dbutils.widgets.text("publish", "true", "PUBLISHED 상태로 배포할지 (true/false)")

p = {k: dbutils.widgets.get(k).strip() for k in ["config_path", "target_domain", "publish"]}
if not p["config_path"]:
    raise ValueError("config_path를 설정하세요")
if not p["target_domain"]:
    raise ValueError("target_domain을 설정하세요 (예: domains/system-general-domain-...)")
print(f"config: {p['config_path']}")
print(f"domain: {p['target_domain']}")
print(f"publish: {p['publish']}")

# COMMAND ----------

import json

with open(p["config_path"], encoding="utf-8") as f:
    config = json.load(f)

pages = config["pages"]
print(f"배포할 페이지: {len(pages)}개")
for pg in pages:
    print(f"  {pg['display_name']} ({pg['state']}, 본문 {len(pg['body'])}자)")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
domain = p["target_domain"]
do_publish = p["publish"].lower() == "true"

# 대상 도메인의 기존 페이지 목록 (제목으로 매칭)
existing = {}
token = None
while True:
    query = {"page_size": 100, "filter": f'domain = "{domain}"'}
    if token:
        query["page_token"] = token
    resp = w.api_client.do("GET", "/api/2.0/knowledge/pages", query=query)
    for ep in resp.get("pages", []):
        existing[ep["display_name"]] = ep["name"].replace("pages/", "")
    token = resp.get("next_page_token")
    if not token or not resp.get("pages"):
        break
print(f"대상 도메인 기존 페이지: {len(existing)}개")

# COMMAND ----------

results = []
for pg in pages:
    title = pg["display_name"]
    state = pg["state"] if do_publish else "DRAFT"
    body = {
        "display_name": title,
        "description": pg.get("description", ""),
        "body": pg.get("body", ""),
        "synonyms": pg.get("synonyms", []),
        "state": state,
    }

    if title in existing:
        pid = existing[title]
        masks = ["display_name", "description", "body", "synonyms", "state"]
        resp = w.api_client.do("PATCH", f"/api/2.0/knowledge/pages/{pid}",
                              query={"update_mask": ",".join(masks)}, body=body)
        results.append({"title": title, "action": "업데이트", "page_id": pid})
        print(f"  업데이트: {title} ({pid})")
    else:
        body["domain"] = domain
        resp = w.api_client.do("POST", "/api/2.0/knowledge/pages", body=body)
        new_id = resp.get("name", "").replace("pages/", "")
        results.append({"title": title, "action": "생성", "page_id": new_id})
        print(f"  생성: {title} ({new_id})")

    # 에셋 링크 복원
    for link in pg.get("asset_links", []):
        pid = results[-1]["page_id"]
        cat = link["category"]
        try:
            w.api_client.do("POST",
                f"/api/2.0/knowledge/pages/{pid}/asset-link-categories/{cat}/asset-links",
                body={"asset_type": link["asset_type"], "asset_id": link["asset_id"]})
        except Exception as e:
            print(f"    에셋 링크 실패: {link} — {e}")

print(f"\n완료: {len(results)}개 페이지 배포")
for r in results:
    print(f"  [{r['action']}] {r['title']} (page_id={r['page_id']})")
