import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface Target {
    id: string;
    domain: string;
    created_at: string;
}

export interface Scan {
    id: string;
    target_id: string;
    status: string;
    phase?: string;
    progress_percent: number;
    started_at: string;
    finished_at?: string;
    config: Record<string, any>;
}

export interface Port {
    id: string;
    port_number: number;
    protocol: string;
    service_name?: string;
    state: string;
    version?: string;
}

export interface Technology {
    id: string;
    name: string;
    version?: string;
    categories?: string[];
}

export interface Subdomain {
    id: string;
    hostname: string;
    ip_address?: string;
    is_alive: boolean;
    status_code?: number;
    title?: string;
    discovered_by?: string;
    ports?: Port[];
    technologies?: Technology[];
    task_status?: string;
}

export interface CrawledPath {
    id: string;
    subdomain_id: string;
    url: string;
    status_code?: number;
    content_type?: string;
    content_length?: number;
    discovered_by?: string;
}

export interface Vulnerability {
    id: string;
    scan_id: string;
    path_id?: string;
    subdomain_id?: string;
    name: string;
    severity?: string;
    description?: string;
    matcher_name?: string;
    extracted_results?: string;
    path_url?: string;
}

// Pagination Response Interface
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    pages: number;
}

export interface PathStats {
    total_paths: number;
    live_count: number;
    tool_counts: Record<string, number>;
}

export interface PathListResponse extends PaginatedResponse<CrawledPath> {
    stats: PathStats;
}

export const targetApi = {
    create: (domain: string): Promise<Target> => api.post<Target>('/targets', { domain }).then((res) => res.data),
    list: (): Promise<Target[]> => api.get<Target[]>('/targets').then((res) => res.data),
    get: (id: string): Promise<Target> => api.get<Target>(`/targets/${id}`).then((res) => res.data),
};

export const scanApi = {
    create: (targetId: string, config: Record<string, any> = {}): Promise<Scan> =>
        api.post<Scan>('/scans', { target_id: targetId, config }).then((res) => res.data),
    list: (): Promise<Scan[]> => api.get<Scan[]>('/scans').then((res) => res.data),
    get: (id: string): Promise<Scan> => api.get<Scan>(`/scans/${id}`).then((res) => res.data),
    getSubdomains: (scanId: string, page = 1, size = 50): Promise<PaginatedResponse<Subdomain>> =>
        api.get<PaginatedResponse<Subdomain>>(`/scans/${scanId}/subdomains`, { params: { page, size } }).then((res) => res.data),
    getPaths: (
        scanId: string,
        page = 1,
        size = 50,
        search?: string,
        status_category?: string,
        tool?: string,
        port?: string
    ): Promise<PathListResponse> =>
        api.get<PathListResponse>(`/scans/${scanId}/paths`, {
            params: { page, size, search, status_category, tool, port }
        }).then((res) => res.data),
    triggerAction: (
        scanId: string,
        subdomainIds: string[],
        action: 'port_scan' | 'tech_profiling' | 'path_crawling' | 'nuclei_scan',
        pathIds?: string[]
    ): Promise<{ message: string; triggered_count: number }> =>
        api.post(`/scans/${scanId}/actions`, { subdomain_ids: subdomainIds, action, path_ids: pathIds }).then((res) => res.data),
    getVulnerabilities: (
        scanId: string,
        page = 1,
        size = 50,
        severity?: string
    ): Promise<PaginatedResponse<Vulnerability>> =>
        api.get<PaginatedResponse<Vulnerability>>(`/scans/${scanId}/vulnerabilities`, {
            params: { page, size, severity }
        }).then((res) => res.data),
};

export interface WorkerStatusResponse {
    status: string;
    data: {
        active: Record<string, any[]>;
        reserved: Record<string, any[]>;
        scheduled: Record<string, any[]>;
        stats: Record<string, any>;
    };
    message?: string;
}

export const workerApi = {
    getStatus: (): Promise<WorkerStatusResponse> => api.get<WorkerStatusResponse>('/workers').then((res) => res.data),
};
