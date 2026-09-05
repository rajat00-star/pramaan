import { apiClient } from './client';
import type { DashboardSummaryOut } from '../types/api';

/** Inspector/department-admin only on the backend (require_roles) — used by
 * the Inspector Home screen for its stat tiles (Pending Reviews, Reviewed
 * Today, Recent Cases). Real aggregate numbers, never fabricated. */
export function fetchDashboardSummary(): Promise<DashboardSummaryOut> {
  return apiClient.get<DashboardSummaryOut>('/api/dashboard/summary');
}
