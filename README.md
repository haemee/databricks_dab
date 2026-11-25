# 카드 소비 분석 Genie 에이전트 번들

카드 소비 분석 Genie 에이전트의 구성을 코드로 관리하고, Declarative Automation Bundle(DAB) job으로 환경별로 배포합니다.

## 구성

| 경로 | 설명 |
| --- | --- |
| `databricks.yml` | 번들 정의, 변수, 대상 환경(dev, prod) |
| `resources/deploy_genie_space.job.yml` | 배포 노트북을 실행하는 job |
| `src/genie_space.json` | 에이전트 구성 원본 (테이블, 볼륨, 지침, 예제 SQL, 시작 질문, 벤치마크) |
| `src/deploy_genie_space.py` | 카탈로그·스키마를 치환한 뒤 Genie API로 에이전트를 생성하거나 업데이트 |

번들 파일은 `card_spend_genie_bundle/` 폴더에 있습니다. 아래 경로는 이 폴더 기준입니다.

## 변수

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `warehouse_id` | SQL 웨어하우스 ID | `2bf795da43858056` |
| `catalog`, `schema` | 배포 대상 카탈로그·스키마 | `hpark_admin_catalog`, `fintech_demo` |
| `space_title` | 에이전트 이름 | dev: `[dev] 카드 소비 분석` |
| `space_id` | 업데이트할 기존 에이전트 ID. 비우면 같은 이름을 찾아 업데이트하고, 없으면 생성 | 빈 값 |
| `parent_path` | 새 에이전트를 만들 폴더 | 사용자 홈 |

`prod` 대상의 `<PROD_...>` 값은 실제 값으로 바꿔야 합니다. 값이 비어 있으면 배포 노트북이 중단됩니다.

## 배포

CLI 명령은 SQL 편집기가 아니라 터미널에서 실행합니다.

```
databricks auth login --host <워크스페이스 URL>
cd card_spend_genie_bundle
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run deploy_genie_space -t dev
```

처음 실행하면 새 에이전트 ID가 출력됩니다. 이 ID를 `space_id` 변수에 지정하면 이후 배포는 같은 에이전트를 업데이트합니다.

CLI 없이 배포하려면 `src/deploy_genie_space.py` 노트북을 열고 위젯 값을 채워 직접 실행합니다. `config_path`에는 `genie_space.json`의 전체 `/Workspace/...` 경로를 넣으세요.

## 구성 변경 절차

1. Genie 에이전트에서 지침이나 예제를 수정합니다.
2. 에이전트 구성을 백업 파일(JSON)로 저장합니다.
3. 백업 파일의 `serialized_space` 내용으로 `src/genie_space.json`을 갱신합니다.
4. 변경 사항을 커밋하고 푸시한 뒤 dev, prod 순서로 배포합니다.

## 주의 사항

* 업데이트하면 에이전트 구성이 `genie_space.json` 내용으로 통째로 대체됩니다.
* 컬럼별 설정과 실행 권한 설정(run-as)은 구성 파일에 포함되지 않습니다. 배포한 뒤 따로 확인하세요.
* 지침 속 기준일(2026-11-15)과 "지난달 = 10월" 규칙은 자동으로 바뀌지 않습니다. 데이터 기간이 다르면 `genie_space.json`에서 직접 수정하세요.
* 원본 에이전트와 같은 `space_title`로 배포하면 원본을 덮어씁니다.
