import { useMutation, useQueryClient } from '@tanstack/react-query';
import { targetApi, scanApi } from '@/services/api';

export function useCreateTarget() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: targetApi.create,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['targets'] });
        },
    });
}

export function useCreateScan() {
    const queryClient = useQueryClient();
    return useMutation({
        // mutationFn은 인자가 하나여야 하므로 객체로 감쌈
        mutationFn: ({ targetId, config }: { targetId: string; config?: any }) =>
            scanApi.create(targetId, config),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['scans'] });
        },
    });
}
