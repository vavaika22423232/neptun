import { useQuery } from '@tanstack/react-query';
import { remoteConfigService } from '../config/remoteConfig';

export function useRemoteConfig() {
  return useQuery({
    queryKey: ['remote-config'],
    queryFn: ({ signal }) => remoteConfigService.fetch(signal),
    staleTime: 10 * 60_000,
    initialData: remoteConfigService.getCached(),
  });
}
