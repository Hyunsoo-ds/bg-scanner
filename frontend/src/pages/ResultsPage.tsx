import React, { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { scanApi, type Scan, type PathListResponse, type Subdomain, type PaginatedResponse, type Vulnerability } from '@/services/api';
import { ArrowLeft, ExternalLink, Search, Globe, BookOpen, Archive, Radar, AlertTriangle, Info, ShieldAlert } from 'lucide-react';

// ── 상태코드 뱃지 ────────────────────────────────────────────────────────────
function StatusBadge({ code }: { code?: number }) {
    if (!code) return <span className="text-xs text-gray-400">—</span>;
    const cls =
        code < 300 ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
            code < 400 ? 'bg-blue-100 text-blue-700 border-blue-200' :
                code < 500 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                    'bg-red-100 text-red-700 border-red-200';
    return (
        <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded border ${cls}`}>
            {code}
        </span>
    );
}

// ── 발견 도구 뱃지 ───────────────────────────────────────────────────────────
const TOOL_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
    katana: { icon: <Radar className="w-3 h-3" />, color: 'bg-purple-100 text-purple-700 border-purple-200', label: 'Katana' },
    dirsearch: { icon: <Search className="w-3 h-3" />, color: 'bg-orange-100 text-orange-700 border-orange-200', label: 'Dirsearch' },
    waybackurls: { icon: <Archive className="w-3 h-3" />, color: 'bg-slate-100 text-slate-700 border-slate-200', label: 'Wayback' },
    gau: { icon: <Globe className="w-3 h-3" />, color: 'bg-teal-100 text-teal-700 border-teal-200', label: 'GAU' },
};

function ToolBadge({ tool }: { tool?: string }) {
    const key = tool?.toLowerCase() ?? '';
    const meta = TOOL_META[key];
    if (!meta) return <span className="text-xs text-gray-400">{tool || '—'}</span>;
    return (
        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border font-medium ${meta.color}`}>
            {meta.icon}{meta.label}
        </span>
    );
}

// ── content-length 포맷 ──────────────────────────────────────────────────────
function formatSize(bytes?: number) {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// ── URL 줄임 표시 ────────────────────────────────────────────────────────────
function TruncatedUrl({ url }: { url: string }) {
    let display = url;
    try {
        const u = new URL(url);
        display = u.pathname + (u.search || '');
        if (display.length > 60) display = display.slice(0, 57) + '…';
    } catch { /* fallback */ }
    return (
        <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-1.5 font-mono text-sm text-blue-600 hover:text-blue-800 hover:underline"
            title={url}
        >
            <span>{display}</span>
            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
        </a>
    );
}

// ── 요약 카드 ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
    return (
        <div className="bg-card border rounded-lg p-4 flex flex-col gap-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
            <span className="text-2xl font-bold">{value}</span>
            {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
        </div>
    );
}

// ── Paths 탭 ─────────────────────────────────────────────────────────────────
// ── Paths 탭 ─────────────────────────────────────────────────────────────────
function PathsTab({ scanId, scan }: { scanId: string; scan?: Scan }) {
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [toolFilter, setToolFilter] = useState<string>('all');

    const [page, setPage] = useState(1);
    const size = 50;

    const { data: pathsData, isLoading } = useQuery<PathListResponse>({
        queryKey: ['paths', scanId, page, search, statusFilter, toolFilter],
        queryFn: () => scanApi.getPaths(
            scanId,
            page,
            size,
            search || undefined,
            statusFilter === 'all' ? undefined : statusFilter,
            toolFilter === 'all' ? undefined : toolFilter
        ),
        refetchInterval: (query) => {
            // 결과가 없으면 계속 폴링 (크롤러가 비동기로 완료되므로)
            const data = query.state.data as PathListResponse | undefined;
            if (!data || data.total === 0) return 5000;
            return false;
        },
        placeholderData: keepPreviousData, // React Query v5 migration
    });

    const paths = pathsData?.items || [];
    const total = pathsData?.total || 0;
    const totalPages = pathsData?.pages || 0;
    const stats = pathsData?.stats;

    // Selection State
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isActionLoading, setIsActionLoading] = useState(false);

    const handleSelectAll = () => {
        if (!paths) return;
        if (selectedIds.size === paths.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(paths.map(p => p.id)));
        }
    };

    const handleSelect = (id: string) => {
        const next = new Set(selectedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedIds(next);
    };

    const handleNucleiScan = async () => {
        if (selectedIds.size === 0) return;
        setIsActionLoading(true);
        try {
            // scanApi needs to be updated to support path_ids
            // For now we assume triggerAction can take path_ids or we modify api calls
            // Since I haven't updated api.ts, I need to check how to call it.
            // The backend expects path_ids in the body.
            // I'll need to check/update services/api.ts as well.
            await scanApi.triggerAction(scanId, [], 'nuclei_scan', Array.from(selectedIds));
            alert(`Nuclei Scan triggered for ${selectedIds.size} paths`);
            setSelectedIds(new Set());
        } catch (err) {
            alert('Failed to trigger Nuclei Scan');
            console.error(err);
        } finally {
            setIsActionLoading(false);
        }
    };


    // Use server-provided stats
    const totalPaths = stats?.total_paths || 0;
    const livePaths = stats?.live_count || 0;
    const toolCounts = stats?.tool_counts || {};

    // 정렬된 Tool Counts
    const sortedTools = useMemo(() => {
        return Object.entries(toolCounts).sort((a, b) => b[1] - a[1]);
    }, [toolCounts]);

    if (isLoading && !pathsData) {
        return (
            <div className="flex items-center justify-center py-20 text-muted-foreground">
                <div className="text-center">
                    <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3" />
                    <p>Loading paths...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-5">
            {/* Action Bar for Paths */}
            <div className="flex items-center justify-between bg-card border rounded-lg p-3 shadow-sm">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground mr-2">
                        {selectedIds.size} selected
                    </span>
                    <button
                        onClick={handleNucleiScan}
                        disabled={selectedIds.size === 0 || isActionLoading}
                        className="px-3 py-1.5 text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200 rounded hover:bg-orange-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        Nuclei Scan
                    </button>
                </div>
            </div>

            {/* 요약 카드 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatCard label="Total Paths" value={totalPaths} />
                <StatCard label="Live (2xx/3xx)" value={livePaths} sub={totalPaths ? `${Math.round(livePaths / totalPaths * 100)}%` : undefined} />
                <StatCard
                    label="Top Tool"
                    value={sortedTools[0]?.[0] ?? '—'}
                    sub={sortedTools[0] ? `${sortedTools[0][1]} URLs` : undefined}
                />
                <StatCard label="Filtered" value={total} sub={`of ${totalPaths}`} />
            </div>

            {/* 도구별 분포 바 */}
            {totalPaths > 0 && (
                <div className="bg-card border rounded-lg p-4">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-3">Discovery Tool Distribution</p>
                    <div className="flex gap-3 flex-wrap">
                        {sortedTools.map(([tool, count]) => {
                            const pct = Math.round(count / totalPaths * 100);
                            return (
                                <button
                                    key={tool}
                                    onClick={() => {
                                        setToolFilter(toolFilter === tool ? 'all' : tool);
                                        setPage(1); // Reset page on filter change
                                    }}
                                    className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-full border transition-all ${toolFilter === tool ? 'ring-2 ring-primary' : 'hover:bg-muted'}`}
                                >
                                    <ToolBadge tool={tool} />
                                    <span className="font-semibold">{count}</span>
                                    <span className="text-muted-foreground text-xs">({pct}%)</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* 필터 바 */}
            <div className="flex flex-wrap gap-2 items-center">
                <div className="relative flex-1 min-w-48">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Filter by URL..."
                        value={search}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
                        className="w-full pl-9 pr-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                </div>
                <select
                    value={statusFilter}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setStatusFilter(e.target.value); setPage(1); }}
                    className="text-sm border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                >
                    <option value="all">All Status</option>
                    <option value="2xx">2xx Success</option>
                    <option value="3xx">3xx Redirect</option>
                    <option value="4xx">4xx Client Error</option>
                    <option value="5xx">5xx Server Error</option>
                    <option value="none">No Status</option>
                </select>
                <select
                    value={toolFilter}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setToolFilter(e.target.value); setPage(1); }}
                    className="text-sm border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                >
                    <option value="all">All Tools</option>
                    <option value="katana">Katana</option>
                    <option value="dirsearch">Dirsearch</option>
                    <option value="waybackurls">Waybackurls</option>
                    <option value="gau">GAU</option>
                </select>
                {(search || statusFilter !== 'all' || toolFilter !== 'all') && (
                    <button
                        onClick={() => { setSearch(''); setStatusFilter('all'); setToolFilter('all'); setPage(1); }}
                        className="text-xs text-muted-foreground hover:text-foreground underline"
                    >
                        Clear filters
                    </button>
                )}
            </div>

            {/* 테이블 */}
            <div className="bg-card border rounded-lg shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-muted text-muted-foreground text-xs uppercase tracking-wide">
                            <tr>
                                <th className="px-4 py-3 w-10">
                                    <input
                                        type="checkbox"
                                        checked={paths && paths.length > 0 && selectedIds.size === paths.length}
                                        onChange={handleSelectAll}
                                        className="rounded border-gray-300 text-primary focus:ring-primary"
                                    />
                                </th>
                                <th className="px-4 py-3 w-[45%]">URL</th>
                                <th className="px-4 py-3">Status</th>
                                <th className="px-4 py-3">Content-Type</th>
                                <th className="px-4 py-3">Size</th>
                                <th className="px-4 py-3">Tool</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {paths.map(p => (
                                <tr key={p.id} className={`hover:bg-muted/40 transition-colors ${selectedIds.has(p.id) ? 'bg-orange-50/50' : ''}`}>
                                    <td className="px-4 py-2.5">
                                        <input
                                            type="checkbox"
                                            checked={selectedIds.has(p.id)}
                                            onChange={() => handleSelect(p.id)}
                                            className="rounded border-gray-300 text-primary focus:ring-primary"
                                        />
                                    </td>
                                    <td className="px-4 py-2.5 max-w-0">
                                        <TruncatedUrl url={p.url} />
                                        {/* 호스트 표시 */}
                                        <span className="block text-xs text-muted-foreground mt-0.5 truncate">
                                            {(() => { try { return new URL(p.url).hostname; } catch { return ''; } })()}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2.5">
                                        <StatusBadge code={p.status_code} />
                                    </td>
                                    <td className="px-4 py-2.5 text-xs text-muted-foreground font-mono">
                                        {p.content_type
                                            ? p.content_type.split(';')[0].trim()
                                            : '—'}
                                    </td>
                                    <td className="px-4 py-2.5 text-xs text-muted-foreground font-mono">
                                        {formatSize(p.content_length)}
                                    </td>
                                    <td className="px-4 py-2.5">
                                        <ToolBadge tool={p.discovered_by} />
                                    </td>
                                </tr>
                            ))}
                            {paths.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                                        {totalPaths === 0
                                            ? <div>
                                                <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-30" />
                                                <p>No paths found yet.</p>
                                                {scan?.phase === 'Path Crawling' ? (
                                                    <div className="mt-2 flex flex-col items-center gap-1">
                                                        <div className="animate-pulse text-xs text-primary font-medium">
                                                            Currently Crawling Paths...
                                                        </div>
                                                        <div className="text-[10px] text-muted-foreground">This may take a few minutes</div>
                                                    </div>
                                                ) : (
                                                    <p className="text-xs mt-1">
                                                        {scan?.status === 'completed'
                                                            ? 'No paths were discovered during the scan.'
                                                            : 'Crawler will run after port scanning.'}
                                                    </p>
                                                )}
                                            </div>
                                            : 'No paths match the current filters.'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                {total > 0 && (
                    <div className="px-4 py-3 border-t bg-muted/30 text-xs text-muted-foreground flex items-center justify-between">
                        <span>Showing {paths.length} of {total} paths (Total: {totalPaths})</span>

                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="px-2 py-1 border rounded bg-background hover:bg-muted disabled:opacity-50"
                            >
                                Previous
                            </button>
                            <span>Page {page} of {totalPages || 1}</span>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page >= totalPages}
                                className="px-2 py-1 border rounded bg-background hover:bg-muted disabled:opacity-50"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// ── Subdomains 탭 ─────────────────────────────────────────────────────────────
function SubdomainsTab({ scanId }: { scanId: string }) {
    const [page, setPage] = useState(1);
    const size = 50;

    const { data: subdomainsData } = useQuery<PaginatedResponse<Subdomain>>({
        queryKey: ['subdomains', scanId, page],
        queryFn: () => scanApi.getSubdomains(scanId, page, size),
        enabled: !!scanId,
        refetchInterval: 5000,
    });

    const subdomains = subdomainsData?.items || [];
    const total = subdomainsData?.total || 0;
    const totalPages = subdomainsData?.pages || 0;

    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isActionLoading, setIsActionLoading] = useState(false);

    // 전체 선택/해제 토글
    const handleSelectAll = () => {
        if (!subdomains) return;
        if (selectedIds.size === subdomains.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(subdomains.map(s => s.id)));
        }
    };

    // 개별 선택 토글
    const handleSelect = (id: string) => {
        const next = new Set(selectedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedIds(next);
    };

    // 액션 실행
    const handleAction = async (action: 'port_scan' | 'tech_profiling' | 'path_crawling') => {
        if (selectedIds.size === 0) return;
        setIsActionLoading(true);
        try {
            const res = await scanApi.triggerAction(scanId, Array.from(selectedIds), action);
            alert(`Action triggered: ${res.message}`);
            // 선택 초기화 (옵션)
            setSelectedIds(new Set());
        } catch (err) {
            alert('Failed to trigger action');
            console.error(err);
        } finally {
            setIsActionLoading(false);
        }
    };

    return (
        <div className="space-y-4">
            {/* 액션 버튼 바 */}
            <div className="flex items-center justify-between bg-card border rounded-lg p-3 shadow-sm">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground mr-2">
                        {selectedIds.size} selected
                    </span>
                    <button
                        onClick={() => handleAction('port_scan')}
                        disabled={selectedIds.size === 0 || isActionLoading}
                        className="px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        Port Scan
                    </button>
                    <button
                        onClick={() => handleAction('tech_profiling')}
                        disabled={selectedIds.size === 0 || isActionLoading}
                        className="px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 rounded hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        Tech Profiling
                    </button>
                    <button
                        onClick={() => handleAction('path_crawling')}
                        disabled={selectedIds.size === 0 || isActionLoading}
                        className="px-3 py-1.5 text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200 rounded hover:bg-purple-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        Path Crawling
                    </button>
                </div>
            </div>

            <div className="bg-card border rounded-lg shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted text-muted-foreground text-xs uppercase tracking-wide">
                        <tr>
                            <th className="px-4 py-3 w-10">
                                <input
                                    type="checkbox"
                                    checked={subdomains && subdomains.length > 0 && selectedIds.size === subdomains.length}
                                    onChange={handleSelectAll}
                                    className="rounded border-gray-300 text-primary focus:ring-primary"
                                />
                            </th>
                            <th className="px-4 py-3">Hostname</th>
                            <th className="px-4 py-3">IP Address</th>
                            <th className="px-4 py-3">IP Address</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3">Task</th>
                            <th className="px-4 py-3">Source</th>
                            <th className="px-4 py-3">Ports</th>
                            <th className="px-4 py-3">Technologies</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {subdomains?.map((sub) => (
                            <tr key={sub.id} className={`hover:bg-muted/40 transition-colors ${selectedIds.has(sub.id) ? 'bg-blue-50/50' : ''}`}>
                                <td className="px-4 py-3">
                                    <input
                                        type="checkbox"
                                        checked={selectedIds.has(sub.id)}
                                        onChange={() => handleSelect(sub.id)}
                                        className="rounded border-gray-300 text-primary focus:ring-primary"
                                    />
                                </td>
                                <td className="px-4 py-3 font-medium cursor-pointer" onClick={() => handleSelect(sub.id)}>{sub.hostname}</td>
                                <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{sub.ip_address || '—'}</td>
                                <td className="px-4 py-3">
                                    {sub.is_alive
                                        ? <span className="text-emerald-600 text-xs px-2 py-0.5 bg-emerald-50 border border-emerald-200 rounded">Alive</span>
                                        : <span className="text-gray-500 text-xs px-2 py-0.5 bg-gray-100 border rounded">Unknown</span>}
                                </td>
                                <td className="px-4 py-3">
                                    {sub.task_status && (
                                        <span
                                            className={`px-2 py-0.5 rounded text-xs border ${sub.task_status.includes('ing')
                                                ? 'bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse'
                                                : sub.task_status.includes('ed')
                                                    ? 'bg-green-500/10 text-green-500 border-green-500/20'
                                                    : 'bg-muted text-muted-foreground border-border'
                                                }`}
                                        >
                                            {sub.task_status}
                                        </span>
                                    )}
                                </td>
                                <td className="px-4 py-3 text-xs text-muted-foreground">{sub.discovered_by || 'subfinder'}</td>
                                <td className="px-4 py-3">
                                    {sub.ports && sub.ports.length > 0 ? (
                                        <div className="flex flex-wrap gap-1">
                                            {sub.ports.slice(0, 5).map(port => (
                                                <span key={port.id} className="text-xs border px-1.5 py-0.5 rounded bg-background font-mono" title={`${port.service_name} ${port.version || ''}`}>
                                                    {port.port_number}/{port.service_name || '?'}
                                                </span>
                                            ))}
                                            {sub.ports.length > 5 && <span className="text-xs text-muted-foreground">+{sub.ports.length - 5}</span>}
                                        </div>
                                    ) : <span className="text-muted-foreground text-xs">—</span>}
                                </td>
                                <td className="px-4 py-3">
                                    {sub.technologies && sub.technologies.length > 0 ? (
                                        <div className="flex flex-wrap gap-1">
                                            {sub.technologies.map(tech => (
                                                <span key={tech.id} className="text-xs border px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border-blue-100" title={tech.categories?.join(', ')}>
                                                    {tech.name}{tech.version && <span className="text-blue-400 ml-0.5 text-[10px]">v{tech.version}</span>}
                                                </span>
                                            ))}
                                        </div>
                                    ) : <span className="text-muted-foreground text-xs">—</span>}
                                </td>
                            </tr>
                        ))}
                        {!subdomains?.length && (
                            <tr>
                                <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">No subdomains found yet.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
                <div className="px-4 py-3 border-t bg-muted/30 text-xs text-muted-foreground flex items-center justify-between">
                    <span>Showing {subdomains.length} of {total} subdomains</span>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="px-2 py-1 border rounded bg-background hover:bg-muted disabled:opacity-50"
                        >
                            Previous
                        </button>
                        <span>Page {page} of {totalPages || 1}</span>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="px-2 py-1 border rounded bg-background hover:bg-muted disabled:opacity-50"
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ── 상세 결과 모달 (간단히) ────────────────────────────────────────────────────────
function VulnerabilityDetails({ vuln }: { vuln: Vulnerability }) {
    if (!vuln.extracted_results) return null;
    return (
        <div className="mt-2 p-3 bg-muted/50 rounded text-xs font-mono whitespace-pre-wrap break-all border">
            {vuln.extracted_results}
        </div>
    );
}

// ── 취약점 뱃지 ──────────────────────────────────────────────────────────────
function SeverityBadge({ severity }: { severity?: string }) {
    if (!severity) return <span className="text-xs text-gray-400">—</span>;
    const sev = severity.toLowerCase();
    let color = 'bg-gray-100 text-gray-700 border-gray-200';
    let icon = <Info className="w-3 h-3" />;

    if (sev === 'critical') {
        color = 'bg-red-100 text-red-700 border-red-200';
        icon = <ShieldAlert className="w-3 h-3" />;
    } else if (sev === 'high') {
        color = 'bg-orange-100 text-orange-700 border-orange-200';
        icon = <AlertTriangle className="w-3 h-3" />;
    } else if (sev === 'medium') {
        color = 'bg-yellow-100 text-yellow-700 border-yellow-200';
        icon = <AlertTriangle className="w-3 h-3" />;
    } else if (sev === 'low') {
        color = 'bg-blue-100 text-blue-700 border-blue-200';
        icon = <Info className="w-3 h-3" />;
    }

    return (
        <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded border capitalize ${color}`}>
            {icon}{severity}
        </span>
    );
}

// ── Vulnerabilities 탭 ───────────────────────────────────────────────────────
function VulnerabilitiesTab({ scanId }: { scanId: string }) {
    const [page, setPage] = useState(1);
    const size = 50;

    const { data: vulnsData, isLoading } = useQuery<PaginatedResponse<Vulnerability>>({
        queryKey: ['vulnerabilities', scanId, page],
        queryFn: () => scanApi.getVulnerabilities(scanId, page, size),
        refetchInterval: 5000,
    });

    const vulns = vulnsData?.items || [];
    const total = vulnsData?.total || 0;
    const totalPages = vulnsData?.pages || 0;

    if (isLoading && !vulnsData) {
        return (
            <div className="py-12 text-center text-muted-foreground">
                <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mx-auto mb-2" />
                Loading vulnerabilities...
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="bg-card border rounded-lg shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted text-muted-foreground text-xs uppercase tracking-wide">
                        <tr>
                            <th className="px-4 py-3">Name</th>
                            <th className="px-4 py-3">Severity</th>
                            <th className="px-4 py-3">Matcher</th>
                            <th className="px-4 py-3 w-[40%]">Description / Details</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {vulns.map(v => (
                            <tr key={v.id} className="hover:bg-muted/40 transition-colors">
                                <td className="px-4 py-3 font-medium align-top">{v.name}</td>
                                <td className="px-4 py-3 align-top">
                                    <SeverityBadge severity={v.severity} />
                                </td>
                                <td className="px-4 py-3 text-xs font-mono text-muted-foreground align-top">
                                    {v.matcher_name || '—'}
                                </td>
                                <td className="px-4 py-3 text-sm text-muted-foreground align-top">
                                    <p className="line-clamp-2">{v.description || 'No description'}</p>
                                    <VulnerabilityDetails vuln={v} />
                                </td>
                            </tr>
                        ))}
                        {vulns.length === 0 && (
                            <tr>
                                <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground">
                                    No vulnerabilities found yet.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
                {total > 0 && (
                    <div className="px-4 py-3 border-t bg-muted/30 text-xs text-muted-foreground flex items-center justify-between">
                        <span>Showing {vulns.length} of {total} vulnerabilities</span>
                        <div className="flex items-center gap-2">
                            <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="px-2 py-1 border rounded bg-background hover:bg-muted disabled:opacity-50">Previous</button>
                            <span>Page {page} of {totalPages || 1}</span>
                            <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages} className="px-2 py-1 border rounded bg-background hover:bg-muted disabled:opacity-50">Next</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// ── 메인 ResultsPage ──────────────────────────────────────────────────────────
type TabId = 'subdomains' | 'paths' | 'vulnerabilities';

export default function ResultsPage() {
    const { scanId } = useParams<{ scanId: string }>();
    const [activeTab, setActiveTab] = useState<TabId>('subdomains');

    const { data: scan } = useQuery<Scan>({
        queryKey: ['scan', scanId],
        queryFn: () => scanApi.get(scanId!),
        enabled: !!scanId,
        refetchInterval: (query) => {
            const data = query.state.data as Scan | undefined;
            if (data && (data.status === 'running' || data.status === 'queued')) return 2000;
            return false;
        },
    });

    const { data: subdomainsData } = useQuery<PaginatedResponse<Subdomain>>({
        queryKey: ['subdomains', scanId, 1], // Page 1 for count
        queryFn: () => scanApi.getSubdomains(scanId!, 1, 1),
        enabled: !!scanId,
    });

    const { data: pathsData } = useQuery<PathListResponse>({
        queryKey: ['paths', scanId, 1], // Page 1 for count
        queryFn: () => scanApi.getPaths(scanId!, 1, 1),
        enabled: !!scanId,
        refetchInterval: (query) => {
            const data = query.state.data as PathListResponse | undefined;
            if (!data || data.total === 0) return 5000;
            return false;
        },
    });

    const { data: vulnsData } = useQuery<PaginatedResponse<Vulnerability>>({
        queryKey: ['vulnerabilities', scanId, 1],
        queryFn: () => scanApi.getVulnerabilities(scanId!, 1, 1),
        enabled: !!scanId,
    });

    if (!scan) return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
    );

    const tabs: { id: TabId; label: string; count?: number }[] = [
        { id: 'subdomains', label: 'Subdomains', count: subdomainsData?.total },
        { id: 'paths', label: 'Paths', count: pathsData?.total },
        { id: 'vulnerabilities', label: 'Vulnerabilities', count: vulnsData?.total },
    ];

    const statusColor =
        scan.status === 'completed' ? 'text-emerald-600 bg-emerald-50 border-emerald-200' :
            scan.status === 'running' ? 'text-blue-600 bg-blue-50 border-blue-200' :
                scan.status === 'failed' ? 'text-red-600 bg-red-50 border-red-200' :
                    'text-gray-600 bg-gray-50 border-gray-200';

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* 헤더 */}
            <Link to="/" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
                <ArrowLeft className="w-4 h-4 mr-1.5" />
                Back to Dashboard
            </Link>

            <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
                <div>
                    <h1 className="text-2xl font-bold mb-1">Scan Results</h1>
                    <p className="text-sm text-muted-foreground font-mono">Scan ID: {scan.id}</p>
                </div>
                <div className="flex items-center gap-3">
                    {/* 진행률 바 */}
                    {scan.status === 'running' && (
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                            {scan.phase && <span className="text-xs font-mono text-primary font-semibold animate-pulse">{scan.phase}</span>}
                            <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                                    style={{ width: `${scan.progress_percent}%` }}
                                />
                            </div>
                            <span>{scan.progress_percent}%</span>
                        </div>
                    )}
                    <span className={`text-xs font-bold px-3 py-1.5 rounded-full border uppercase tracking-wide ${statusColor}`}>
                        {scan.status}
                    </span>
                </div>
            </div>

            {/* 탭 네비게이션 */}
            <div className="flex gap-1 border-b mb-6">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px flex items-center gap-2 ${activeTab === tab.id
                            ? 'border-primary text-primary'
                            : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
                            }`}
                    >
                        {tab.label}
                        {tab.count !== undefined && (
                            <span className={`text-xs px-1.5 py-0.5 rounded-full font-mono ${activeTab === tab.id ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                                }`}>
                                {tab.count}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* 탭 콘텐츠 */}
            {activeTab === 'subdomains' && <SubdomainsTab scanId={scanId!} />}
            {activeTab === 'paths' && <PathsTab scanId={scanId!} scan={scan} />}
            {activeTab === 'vulnerabilities' && <VulnerabilitiesTab scanId={scanId!} />}
        </div>
    );
}
