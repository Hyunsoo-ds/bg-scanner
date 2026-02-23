# 📘 BG-Scanner 기술 문서 (Technical Documentation)

이 문서는 BG-Scanner 시스템의 내부 동작 원리, 아키텍처, 데이터 흐름을 상세하게 설명합니다. 개발자가 아니더라도 시스템의 구조를 이해하고, 문제가 발생했을 때 원인을 파악할 수 있도록 돕는 것이 목적입니다.

---

## 1. 프로젝트 개요

BG-Scanner는 **버그바운티(Bug Bounty) 정찰 업무를 자동화**하는 도구입니다.

사용자가 `target.com` 같은 도메인을 입력하면, 시스템은 자동으로 다음 단계를 수행합니다:
1.  **서브도메인 찾기**: `api.target.com`, `dev.target.com` 등을 수집
2.  **포트 스캔**: 각 서브도메인에서 열려있는 포트(80, 443, 8080 등) 확인
3.  **경로 크롤링**: 웹사이트 내의 숨겨진 페이지나 API 엔드포인트 수집
4.  **취약점 스캔**: 알려진 보안 취약점(CVE) 자동 점검

이 모든 과정은 **백그라운드**에서 비동기적으로 실행되며, 사용자는 웹 대시보드에서 실시간으로 결과를 확인할 수 있습니다.

---

## 2. 시스템 아키텍처 (전체 구조)

BG-Scanner는 5개의 독립적인 서비스가 서로 협력하며 동작합니다.

```mermaid
graph TD
    User[사용자 (브라우저)] -->|1. 스캔 요청| UI[Frontend (React)]
    UI -->|2. API 호출 (POST /scans)| API[Backend API (FastAPI)]
    
    API -->|3. 스캔 정보 저장| DB[(PostgreSQL 데이터베이스)]
    API -->|4. 작업 큐에 등록| Broker[(Redis 메시지 브로커)]
    
    Broker -->|5. 작업 가져오기| Worker[Celery Worker (백그라운드 작업자)]
    
    subgraph Scanning Logic
        Worker -->|6. 도구 실행| Tools[Subfinder / Nmap / Katana / Nuclei]
        Tools -->|7. 결과 파싱| Worker
    end
    
    Worker -->|8. 결과 저장| DB
    
    UI -->|9. 진행상황 폴링/조회| API
    API -->|10. 데이터 조회| DB
```

### 각 컴포넌트의 역할

| 컴포넌트 | 기술 스택 | 역할 | 비유 |
|:---:|:---:|:---|:---|
| **Frontend** | React, Vite | 사용자가 보는 화면. 스캔을 요청하고 결과를 보여줍니다. | **레스토랑의 홀 (웨이터 & 메뉴판)** |
| **Backend** | Python, FastAPI | 프론트엔드의 요청을 받아 처리하고, DB와 통신합니다. | **주방의 매니저 (주문 접수 & 지휘)** |
| **Worker** | Celery | 실제 스캔 작업을 수행합니다. 시간이 오래 걸리는 일을 전담합니다. | **주방의 요리사 (실제 요리)** |
| **Broker** | Redis | 백엔드와 워커 사이의 작업 대기열(Queue)입니다. | **주문서 꽂이** |
| **Database** | PostgreSQL | 모든 데이터(타겟, 스캔 결과, 취약점 등)를 영구 저장합니다. | **창고 & 장부** |

---

## 3. 핵심 기술 상세 설명

### 3.1 백엔드 (Backend API)
- **FastAPI**: Python으로 작성된 고성능 웹 프레임워크입니다.
- **역할**:
    - 스캔 시작 요청을 받으면 DB에 '스캔 기록'을 생성하고, 상태를 `queued`(대기중)로 설정합니다.
    - 그리고 Redis(주문서 꽂이)에 "이 스캔 ID로 작업을 시작해!"라는 메시지를 남깁니다.
    - **중요**: 백엔드 API 서버는 직접 스캔을 하지 않습니다. 스캔이 끝날 때까지 기다리지 않고 "작업이 등록되었습니다"라고 즉시 응답합니다. (비동기 처리)

### 3.2 워커 (Celery Worker)
- **Celery**: Python 분산 작업 큐 시스템입니다.
- **역할**:
    - Redis를 계속 감시하다가 새 작업이 들어오면 즉시 가져갑니다.
    - 도커 컨테이너 내부에 설치된 보안 도구(`subfinder`, `nmap` 등)를 실제로 실행(subprocess)합니다.
    - 도구의 실행 결과를 파싱(해석)하여 DB에 저장합니다.
    - 하나의 단계가 끝나면 다음 단계의 작업을 자동으로 큐에 등록합니다. (예: 서브도메인 찾기가 끝나면 -> 포트 스캔 예약)

### 3.3 프론트엔드 (Frontend)
- **React + TanStack Query**: 사용자 인터페이스입니다.
- **역할**:
    - 사용자가 "스캔 시작"을 누르면 백엔드로 요청을 보냅니다.
    - **폴링(Polling)**: 백엔드에 주기적(예: 3초마다)으로 "스캔 끝났어? 진행률 몇 %야?"라고 물어봅니다.
    - DB에 새로운 데이터가 저장되면, 이 폴링 응답에 포함되어 화면이 업데이트됩니다.

---

## 4. 데이터 흐름 (Life of a Scan)

"데이터를 불러오지 못하는 오류"를 해결하기 위해, 데이터가 어떻게 흐르는지 정확히 이해해야 합니다.

### 단계 1: 스캔 시작 요청
1. 사용자가 웹에서 `example.com` 입력 후 [Start Scan] 클릭.
2. **Frontend** -> **Backend**: `POST /api/scans` 요청 전송.
3. **Backend**:
    - DB `scans` 테이블에 레코드 생성 (Status: `queued`).
    - Redis에 `run_subdomain_scan` 작업 메시지 전송.
    - Frontend에 `scan_id` 반환.

### 단계 2: 서브도메인 수집 (Subdomain Enumeration)
1. **Worker**: Redis에서 작업을 꺼내감.
2. **Worker**: DB `scans` 테이블의 상태를 `running`으로 변경.
3. **Worker**: `subfinder -d example.com` 명령어 실행.
4. **Worker**: 명령어 출력을 파싱하여 JSON으로 변환.
5. **Worker**: DB `subdomains` 테이블에 결과 저장 (`INSERT`).
6. **Worker**: 발견된 서브도메인 개수만큼 `run_port_scan` 작업을 Redis에 추가 등록 (Fan-out 패턴).

### 단계 3: 포트 스캔 (Port Scanning)
1. **Worker** (또 다른 프로세스): Redis에서 포트 스캔 작업을 꺼내감.
2. **Worker**: `nmap -p- <IP>` 실행.
3. **Worker**: 결과를 파싱하여 DB `ports` 테이블에 저장.

> **💡 문제 포인트**:
> 만약 2단계나 3단계에서 **Worker가 죽어있거나 에러가 나면**, DB에는 아무것도 저장되지 않습니다.
> Frontend는 계속 폴링을 하지만, 백엔드는 줄 데이터가 없으므로 빈 화면이 나옵니다.

---

## 5. 데이터베이스 스키마 (ERD)

데이터가 어디에 저장되는지 알면 디버깅이 쉬워집니다.

- **targets**: 스캔 대상 도메인 (`id`, `domain`)
- **scans**: 개별 스캔 작업 (`id`, `target_id`, `status`, `created_at`)
    - `status`: `queued` -> `running` -> `completed` (또는 `failed`)
- **subdomains**: 발견된 서브도메인 (`id`, `scan_id`, `hostname`, `ip_address`)
- **ports**: 오픈 포트 정보 (`id`, `subdomain_id`, `port_number`, `service`)
- **paths**: 발견된 URL 경로 (`id`, `subdomain_id`, `url`, `status_code`)

---

## 6. 트러블슈팅 가이드 (문제 해결)

"데이터가 안 보인다"는 문제가 발생했을 때 확인해야 할 체크리스트입니다.

### 6.1 컨테이너 상태 확인
가장 먼저, 모든 서비스가 정상적으로 실행 중인지 확인하세요.
```bash
docker compose ps
```
- `worker` 컨테이너가 `Up` 상태여야 합니다. 만약 `Exit` 상태라면 스캔이 돌지 않습니다.

### 6.2 워커 로그 확인 (가장 중요)
백엔드 에러가 아니라면 90%는 워커 문제입니다.
```bash
docker compose logs -f worker
```
- 로그에 `Received task: app.workers.subdomain_task.run_subdomain_scan` 메시지가 보이나요?
- 에러 메시지(Traceback)가 있나요?
- 도구 실행 오류(`Command not found` 등)가 있나요?

### 6.3 Redis 연결 확인
백엔드와 워커가 Redis를 통해 소통하고 있는지 확인합니다.
```bash
docker compose logs -f redis
```
- 연결(Connection) 로그가 주기적으로 찍혀야 합니다.

### 6.4 데이터베이스 직접 조회
DB에 데이터가 들어갔능데 프론트엔드에서 못 불러오는 것인지, 아니면 애초에 안 들어간 것인지 확인합니다.
```bash
# DB 컨테이너 접속
docker compose exec postgres psql -U bgscanner bgscanner

# 테이블 데이터 확인
SELECT * FROM scans ORDER BY started_at DESC LIMIT 5;
SELECT * FROM subdomains WHERE scan_id = '문제의_스캔_ID';
```

### 6.5 흔한 원인들
1.  **도구 누락**: `worker` 이미지 빌드 시 `subfinder` 등이 제대로 설치되지 않음.
2.  **네트워크 문제**: 도커 컨테이너 내부에서 외부 인터넷 접속이 차단됨 (DNS 문제 등).
3.  **타임아웃**: 대상 도메인이 응답하지 않아 도구가 무한 대기 상태에 빠짐.
4.  **DB 락**: 비동기 처리가 꼬여서 DB 트랜잭션이 닫히지 않음.

---

## 7. 결론

BG-Scanner는 **비동기 메시지 큐** 방식의 시스템입니다. "요청"과 "처리"가 분리되어 있습니다.
따라서 문제가 생겼을 때는 **어느 단계에서 흐름이 끊겼는지(Queue -> Worker -> Tool -> DB)** 추적하는 것이 핵심입니다.

위의 '트러블슈팅 가이드'를 따라 로그를 확인해보시면 원인을 찾을 수 있을 것입니다.
