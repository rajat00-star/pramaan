import { apiClient } from './client';
import type { AuditLogOut, ReplayOut, ReviewCorrectionIn, ScanOut, ScanSummaryOut, Verdict } from '../types/api';

export interface PickedImage {
  uri: string;
  mimeType: string;
  fileName: string;
}

/** Uploads a real picked image to the real pipeline. The mobile app never
 * evaluates compliance itself — this is the ONLY way a verdict is produced. */
export function createScan(image: PickedImage): Promise<ScanOut> {
  const form = new FormData();
  // React Native's fetch FormData accepts this {uri, name, type} shape directly.
  form.append('file', { uri: image.uri, name: image.fileName, type: image.mimeType } as unknown as Blob);
  return apiClient.postForm<ScanOut>('/api/scans', form);
}

export function listScans(params?: { verdictFilter?: Verdict; statusFilter?: string; limit?: number }): Promise<ScanSummaryOut[]> {
  const query = new URLSearchParams();
  if (params?.verdictFilter) query.set('verdict_filter', params.verdictFilter);
  if (params?.statusFilter) query.set('status_filter', params.statusFilter);
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiClient.get<ScanSummaryOut[]>(`/api/scans${qs ? `?${qs}` : ''}`);
}

export function getScan(scanId: string): Promise<ScanOut> {
  return apiClient.get<ScanOut>(`/api/scans/${scanId}`);
}

export function submitReview(scanId: string, correction: ReviewCorrectionIn): Promise<ScanOut> {
  return apiClient.post<ScanOut>(`/api/scans/${scanId}/review`, correction);
}

export function getAuditTrail(scanId: string): Promise<AuditLogOut[]> {
  return apiClient.get<AuditLogOut[]>(`/api/scans/${scanId}/audit`);
}

export function getReplay(scanId: string): Promise<ReplayOut> {
  return apiClient.get<ReplayOut>(`/api/scans/${scanId}/replay`);
}
