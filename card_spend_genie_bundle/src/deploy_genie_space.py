# Databricks notebook source
# MAGIC %md
# MAGIC 카드 소비 분석 Genie 에이전트 배포
# MAGIC
# MAGIC `genie_space.json`의 구성에서 카탈로그·스키마를 대상 환경 값으로 바꾼 뒤 Genie API로 에이전트를 생성하거나 업데이트합니다.
# MAGIC 업데이트 시 구성(테이블, 지침, 예제 SQL, 시작 질문, 벤치마크)이 파일 내용으로 대체됩니다.

# COMMAND ----------

dbutils.widgets.text("config_path", "")
dbutils.widgets.text("warehouse_id", "")
dbutils.widgets.text("source_catalog", "hpark_admin_catalog")
dbutils.widgets.text("source_schema", "fintech_demo")
dbutils.widgets.text("catalog", "hpark_admin_catalog")
dbutils.widgets.text("schema", "fintech_demo")
dbutils.widgets.text("space_title", "")
dbutils.widgets.text("space_id", "")
dbutils.widgets.text("parent_path", "")

p = {k: dbutils.widgets.get(k).strip() for k in [
    "config_path", "warehouse_id", "source_catalog", "source_schema",
    "catalog", "schema", "space_title", "space_id", "parent_path"]}

for required in ["config_path", "warehouse_id", "catalog", "schema"]:
    if not p[required] or p[required].startswith("<"):
        raise ValueError(f"'{required}' 값을 설정하세요: {p[required]!r}")

# COMMAND ----------

import json

with open(p["config_path"], encoding="utf-8") as f:
    config = json.load(f)

title = p["space_title"] or config["title"]
description = config.get("description", "")
serialized = json.dumps(config["serialized_space"], ensure_ascii=False, indent=2)

# 카탈로그·스키마 치환 (일반 표기, 백틱 표기, 볼륨 경로)
src_c, src_s, dst_c, dst_s = p["source_catalog"], p["source_schema"], p["catalog"], p["schema"]
if (src_c, src_s) != (dst_c, dst_s):
    replacements = [
        (f"{src_c}.{src_s}.", f"{dst_c}.{dst_s}."),
        (f"`{src_c}`.`{src_s}`.", f"`{dst_c}`.`{dst_s}`."),
        (f"/Volumes/{src_c}/{src_s}/", f"/Volumes/{dst_c}/{dst_s}/"),
    ]
    for old, new in replacements:
        serialized = serialized.replace(old, new)
        description = description.replace(f"{src_c}.{src_s}", f"{dst_c}.{dst_s}")
    leftover = serialized.count(src_c) if src_c != dst_c else 0
    if leftover:
        print(f"주의: 치환되지 않은 '{src_c}' 참조가 {leftover}건 남아 있습니다. 구성 파일을 확인하세요.")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()


def find_space_by_title(t):
    token = None
    while True:
        query = {"page_size": 100}
        if token:
            query["page_token"] = token
        resp = w.api_client.do("GET", "/api/2.0/genie/spaces", query=query)
        for s in resp.get("spaces", []):
            if s.get("title") == t:
                return s.get("space_id")
        token = resp.get("next_page_token")
        if not token:
            return None


space_id = p["space_id"] or find_space_by_title(title)

body = {
    "title": title,
    "description": description,
    "warehouse_id": p["warehouse_id"],
    "serialized_space": serialized,
}

if space_id:
    resp = w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)
    action = "업데이트"
else:
    if p["parent_path"]:
        body["parent_path"] = p["parent_path"]
    resp = w.api_client.do("POST", "/api/2.0/genie/spaces", body=body)
    space_id = resp.get("space_id", space_id)
    action = "생성"

print(f"Genie 에이전트 {action} 완료: {title} (space_id={space_id})")
print(f"다음 배포부터는 space_id 변수에 {space_id} 를 지정하면 이름 변경과 관계없이 같은 에이전트를 업데이트합니다.")
dbutils.jobs.taskValues.set("space_id", space_id)
