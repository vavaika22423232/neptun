import { ApiError } from '../../../services/apiClient';

/** Session flag: `/api/v1/*` monetization routes missing on this backend. */
let v1Available: boolean | null = null;
let unavailableLogged = false;

export function isV1MonetizationBackendAvailable(): boolean {
  return v1Available !== false;
}

export function noteV1MonetizationHttpError(error: unknown): void {
  if (!(error instanceof ApiError) || error.status !== 404) return;
  v1Available = false;
}

export function shouldLogV1MonetizationUnavailable(): boolean {
  if (v1Available !== false || unavailableLogged) return false;
  unavailableLogged = true;
  return true;
}
