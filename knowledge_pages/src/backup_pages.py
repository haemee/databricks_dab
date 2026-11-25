# Databricks notebook source
# MAGIC %md
# MAGIC # Knowledge Pages 백업
# MAGIC
# MAGIC 지정한 도메인에서 특정 소유자의 페이지를 읽어 `knowledge_pages.json`으로 저장합니다.
# MAGIC 이 노트북을 실행하면 Git 폴더의 JSON 파일이 최신 상태로 갱신됩니다. 커밋하면 변경 이력이 남습니다.

# COMMAND ----------

dbutils.widgets.text("output_path", "", "JSON 저장 경로 (전체 /Workspace/... 경로)")
dbutils.widgets.text("domain_id", "system-general-domain-05d08df7-ae03-43ad-bbae-14babb530ec0", "도메인 ID")
dbutils.widgets.text("owner_id", "", "소유자 ID (비우면 도메인 전체)")

p = {k: dbutils.widgets.get(k).strip() for k in ["output_path", "domain_id", "owner_id"]}
if not p["output_path"]:
    raise ValueError("output_path를 설정하세요")
print(f"output: {p['output_path']}")
print(f"domain: {p['domain_id']}")
print(f"owner:  {p['owner_id'] or '(전체)'}")

# COMMAND ----------

from databricks.sdk import WorkspaceClient
import concurrent.futures, json, datetime

w = WorkspaceClient()
domain = f'domains/{p["domain_id"]}'

# 도메인 페이지 목록
page_list = []
token = None
while True:
    query = {"page_size": 100, "filter": f'domain = "{domain}"'}
    if token:
        query["page_token"] = token
    resp = w.api_client.do("GET", "/api/2.0/knowledge/pages", query=query)
    page_list.extend(resp.get("pages", []))
    token = resp.get("next_page_token")
    if not token or not resp.get("pages"):
        break
print(f"도메인 페이지: {len(page_list)}개")

# COMMAND ----------

def get_full(name):
    pid = name.replace("pages/", "")
    try:
        detail = w.api_client.do("GET", f"/api/2.0/knowledge/pages/{pid}")
        if p["owner_id"] and p["owner_id"] not in detail.get("owner_ids", []):
            return None
        # 에셋 링크
        links = []
        for cat in ["SOURCE", "RELATED_ASSETS"]:
            try:
                lr = w.api_client.do("GET", f"/api/2.0/knowledge/pages/{pid}/asset-link-categories/{cat}/asset-links")
                for lk in lr.get("asset_links", []):
                    links.append({"category": cat, "asset_type": lk.get("asset_type"), "asset_id": lk.get("asset_id"), "title": lk.get("title", "")})
            except:
                pass
        detail["_asset_links"] = links
        return detail
    except:
        return None

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    results = list(ex.map(lambda pg: get_full(pg["name"]), page_list))

my_pages = [r for r in results if r]
print(f"대상 페이지: {len(my_pages)}개")

# COMMAND ----------

export = {
    "export_version": 1,
    "source_domain": domain,
    "exported_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "pages": []
}
for pg in my_pages:
    export["pages"].append({
        "page_id": pg["name"].replace("pages/", ""),
        "display_name": pg["display_name"],
        "description": pg.get("description", ""),
        "body": pg.get("body", ""),
        "synonyms": pg.get("synonyms", []),
        "state": pg.get("state", "DRAFT"),
        "asset_links": pg.get("_asset_links", [])
    })

with open(p["output_path"], "w", encoding="utf-8") as f:
    json.dump(export, f, ensure_ascii=False, indent=2)

print(f"\n저장 완료: {p['output_path']}")
for pg in export["pages"]:
    print(f"  [{pg['state']}] {pg['display_name']} (본문 {len(pg['body'])}자, 동의어 {len(pg['synonyms'])}개)")
