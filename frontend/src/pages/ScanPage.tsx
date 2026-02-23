import { useState } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { targetApi, scanApi } from '@/services/api';
import { useNavigate } from 'react-router-dom';

export default function ScanPage() {
    const [domain, setDomain] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const createTargetMutation = useMutation({
        mutationFn: targetApi.create,
    });

    const createScanMutation = useMutation({
        mutationFn: ({ targetId }: { targetId: string }) => scanApi.create(targetId),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['scans'] });
            navigate(`/scans/${data.id}`);
        },
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!domain) return;
        setLoading(true);

        try {
            // 1. Target 생성 (이미 존재하면 에러 날 수 있음 - 핸들링 필요하지만 일단 진행)
            let targetId;
            try {
                const target = await createTargetMutation.mutateAsync(domain);
                targetId = target.id;
            } catch (err: any) {
                // 이미 존재하면 목록에서 찾거나 에러 메시지 파싱
                // 여기서는 간단히 목록에서 domain으로 찾아서 ID 가져오는 로직 추가
                const targets = await targetApi.list();
                const existing = targets.find((t) => t.domain === domain);
                if (existing) {
                    targetId = existing.id;
                } else {
                    alert('Failed to create target');
                    setLoading(false);
                    return;
                }
            }

            // 2. Scan 시작
            await createScanMutation.mutateAsync({ targetId });
        } catch (err) {
            console.error(err);
            alert('Failed to start scan');
        } finally {
            setLoading(false);
        }
    };

    const { data: recentScans } = useQuery({
        queryKey: ['scans'],
        queryFn: scanApi.list,
    });

    return (
        <div className="p-8 max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold mb-8">Start New Scan</h1>

            <div className="bg-card border rounded-lg p-6 mb-8 shadow-sm">
                <form onSubmit={handleSubmit} className="flex gap-4">
                    <input
                        type="text"
                        placeholder="Enter domain (e.g., example.com)"
                        className="flex-1 px-4 py-2 border rounded-md bg-background"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-primary text-primary-foreground px-6 py-2 rounded-md font-medium disabled:opacity-50"
                    >
                        {loading ? 'Starting...' : 'Start Scan'}
                    </button>
                </form>
            </div>

            <h2 className="text-xl font-semibold mb-4">Recent Scans</h2>
            <div className="bg-card border rounded-lg shadow-sm overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-muted text-muted-foreground">
                        <tr>
                            <th className="p-4">Target</th>
                            <th className="p-4">Status</th>
                            <th className="p-4">Started At</th>
                            <th className="p-4">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {recentScans?.map((scan) => (
                            <tr key={scan.id} className="hover:bg-muted/50">
                                <td className="p-4">{scan.target_id}</td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded text-xs font-medium 
                        ${scan.status === 'completed' ? 'bg-green-100 text-green-800' :
                                            scan.status === 'running' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                                        {scan.status}
                                    </span>
                                </td>
                                <td className="p-4">{new Date(scan.started_at).toLocaleString()}</td>
                                <td className="p-4">
                                    <button
                                        onClick={() => navigate(`/scans/${scan.id}`)}
                                        className="text-sm text-blue-600 hover:underline"
                                    >
                                        View Results
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {!recentScans?.length && (
                            <tr>
                                <td colSpan={4} className="p-8 text-center text-muted-foreground">No scans found</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
