from typing import List, Dict, Any
from urllib.parse import urlparse, urlunparse


class PathMerger:
    """
    여러 크롤링 도구의 URL 결과를 병합·정규화·중복 제거합니다.

    병합 전략:
    - URL 합집합 (union)
    - URL 정규화 (소문자 scheme/host, 경로 정규화)
    - 중복 URL 제거 (정규화된 URL 기준, 첫 발견 도구 우선)
    - 필터링 옵션 (404, 빈 URL 등)
    """

    # 기본 제외 상태코드
    DEFAULT_EXCLUDE_STATUS = {404}

    def merge(
        self,
        results_list: List[List[Dict[str, Any]]],
        exclude_status: set = None,
        max_urls: int = 5000,
    ) -> List[Dict[str, Any]]:
        """
        Args:
            results_list: 각 스캐너의 결과 리스트 목록
            exclude_status: 제외할 HTTP 상태코드 집합 (기본: {404})
            max_urls: 최대 URL 수 (DoS 방지)
        Returns:
            정규화·중복 제거된 URL 결과 리스트
        """
        if exclude_status is None:
            exclude_status = self.DEFAULT_EXCLUDE_STATUS

        seen: Dict[str, Dict[str, Any]] = {}  # normalized_url → entry

        for results in results_list:
            for entry in results:
                url = entry.get("url", "").strip()
                if not url or not url.startswith("http"):
                    continue

                # 상태코드 필터링
                status = entry.get("status_code")
                if status is not None and status in exclude_status:
                    continue

                normalized = self._normalize_url(url)
                if not normalized:
                    continue

                # 중복 제거: 먼저 발견한 도구 우선
                if normalized not in seen:
                    seen[normalized] = {
                        "url": normalized,
                        "status_code": entry.get("status_code"),
                        "content_type": entry.get("content_type"),
                        "content_length": entry.get("content_length"),
                        "discovered_by": entry.get("discovered_by", "unknown"),
                    }
                else:
                    # status_code가 없으면 나중 결과로 보완
                    existing = seen[normalized]
                    if existing.get("status_code") is None and entry.get("status_code") is not None:
                        existing["status_code"] = entry["status_code"]
                    if existing.get("content_type") is None and entry.get("content_type") is not None:
                        existing["content_type"] = entry["content_type"]
                    if existing.get("content_length") is None and entry.get("content_length") is not None:
                        existing["content_length"] = entry["content_length"]

                if len(seen) >= max_urls:
                    break

        return list(seen.values())

    def _normalize_url(self, url: str) -> str:
        """
        URL 정규화:
        - scheme, host 소문자
        - 기본 포트 제거 (http:80, https:443)
        - 경로 끝 슬래시 통일 (제거)
        - 프래그먼트(#) 제거
        """
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()

            # 기본 포트 제거
            if netloc.endswith(":80") and scheme == "http":
                netloc = netloc[:-3]
            elif netloc.endswith(":443") and scheme == "https":
                netloc = netloc[:-4]

            path = parsed.path.rstrip("/") or "/"
            # 쿼리스트링은 유지 (경로 발견 목적)
            query = parsed.query

            normalized = urlunparse((scheme, netloc, path, "", query, ""))
            return normalized
        except Exception:
            return ""
