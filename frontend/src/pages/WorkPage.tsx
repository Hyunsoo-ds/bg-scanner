import { useQuery } from '@tanstack/react-query';
import { workerApi, WorkerStatusResponse } from '@/services/api';

export default function WorkPage() {
    const { data, isLoading, isError, error } = useQuery<WorkerStatusResponse, Error>({
        queryKey: ['workerStatus'],
        queryFn: workerApi.getStatus,
        refetchInterval: 5000, // Poll every 5 seconds
    });

    if (isLoading) return <div className="p-8">Loading worker status...</div>;
    if (isError) return <div className="p-8 text-red-500">Error loading worker status: {error?.message}</div>;

    const activeTasks = data?.data?.active || {};
    const reservedTasks = data?.data?.reserved || {};

    // Flatten tasks for easier rendering if multiple workers exist
    const getAllTasks = (taskMap: Record<string, any[]>) => {
        const all: { worker: string; task: any }[] = [];
        Object.entries(taskMap).forEach(([workerName, tasks]) => {
            tasks.forEach(task => {
                all.push({ worker: workerName, task });
            });
        });
        return all;
    };

    const activeList = getAllTasks(activeTasks);
    const reservedList = getAllTasks(reservedTasks);

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <h1 className="text-3xl font-bold mb-8">Worker Status</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Active Tasks Panel */}
                <div className="bg-card border rounded-lg shadow-sm flex flex-col">
                    <div className="p-4 border-b bg-muted/30">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <span className="relative flex h-3 w-3">
                                {activeList.length > 0 && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                            </span>
                            Currently Running ({activeList.length})
                        </h2>
                    </div>
                    <div className="p-4 overflow-auto max-h-[500px]">
                        {activeList.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">No tasks currently running</p>
                        ) : (
                            <div className="space-y-4">
                                {activeList.map((item, idx) => (
                                    <div key={idx} className="bg-muted p-4 rounded-md text-sm break-all">
                                        <div className="font-semibold text-primary mb-1">{item.task.name}</div>
                                        <div className="text-xs text-muted-foreground mb-2">Worker: {item.worker}</div>
                                        {item.task.args && (
                                            <div className="mt-2 text-xs font-mono bg-background p-2 rounded">
                                                Args: {JSON.stringify(item.task.args)}
                                            </div>
                                        )}
                                        {item.task.kwargs && Object.keys(item.task.kwargs).length > 0 && (
                                            <div className="mt-1 text-xs font-mono bg-background p-2 rounded">
                                                Kwargs: {JSON.stringify(item.task.kwargs)}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Queued Tasks Panel */}
                <div className="bg-card border rounded-lg shadow-sm flex flex-col">
                    <div className="p-4 border-b bg-muted/30">
                        <h2 className="text-xl font-semibold text-blue-600 flex items-center gap-2">
                            Queued Tasks ({reservedList.length})
                        </h2>
                    </div>
                    <div className="p-4 overflow-auto max-h-[500px]">
                        {reservedList.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">Queue is empty</p>
                        ) : (
                            <div className="space-y-4">
                                {reservedList.map((item, idx) => (
                                    <div key={idx} className="bg-muted p-4 rounded-md text-sm border-l-4 border-blue-500 break-all">
                                        <div className="font-semibold">{item.task.name}</div>
                                        {item.task.args && (
                                            <div className="mt-2 text-xs font-mono bg-background p-2 rounded">
                                                Args: {JSON.stringify(item.task.args)}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Raw Worker Stats */}
            <div className="mt-8">
                <h2 className="text-xl font-semibold mb-4 text-muted-foreground">Raw Worker Stats</h2>
                <div className="bg-card border rounded-lg shadow-sm p-4 overflow-auto max-h-[300px]">
                    <pre className="text-xs font-mono text-muted-foreground">
                        {JSON.stringify(data?.data?.stats, null, 2)}
                    </pre>
                </div>
            </div>
        </div>
    );
}
