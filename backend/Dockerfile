FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 및 보안 도구 설치
# 1. 기본 유틸리티
# 2. Subfinder (Go 설치 후 빌드)
# 3. Nmap
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libpq-dev \
    nmap \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Go 설치 (Subfinder 빌드용)
RUN wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Subfinder 설치
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
# Webanalyze 설치 (Wappalyzer Go Port)
RUN go install -v github.com/rverton/webanalyze/cmd/webanalyze@latest
ENV PATH=$PATH:/root/go/bin
# technologies.json 사전 다운로드 (webanalyze 실행 시 필요)
RUN webanalyze -update || true

# Katana 설치
RUN go install github.com/projectdiscovery/katana/cmd/katana@latest

# Waybackurls 설치
RUN go install github.com/tomnomnom/waybackurls@latest


# GAU 설치
RUN go install github.com/lc/gau/v2/cmd/gau@latest

# Nuclei 설치
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
# Nuclei 템플릿 업데이트 (실행 시 다운로드 방지)
RUN nuclei -update-templates || true

# Python 의존성 설치
COPY requirements.txt .
# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir dirsearch

# 소스 코드 복사
COPY . .

# 실행 권한 부여 (필요 시)
RUN chmod +x /app/start.sh || true

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
