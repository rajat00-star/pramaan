import { File, UploadTask, UploadType } from 'expo-file-system';

import { apiClient, apiUrl, getAuthToken, notifyUnauthorized } from './client';
import { ApiError, PhotoUploadError } from './errors';
import type { AuditLogOut, ReplayOut, ReviewCorrectionIn, ScanOut, ScanSummaryOut, Verdict } from '../types/api';

export interface PickedImage {
  uri: string;
  mimeType: string;
  fileName: string;
}

/**
 * Uploads a real picked image to the real pipeline. The mobile app never
 * evaluates compliance itself — this is the ONLY way a verdict is produced.
 *
 * This deliberately does NOT use fetch()+FormData (see the removed
 * apiClient.postForm and the RequestOptions.formData branch in client.ts).
 * On a physical iOS device, fetch()'s FormData implementation rejected every
 * multipart upload of a picker-provided file with
 * `Error: Unsupported FormDataPart implementation` before any request left
 * the device (confirmed via a live device diagnostic — no request ever
 * reached the backend). This is a real-world break in React Native's
 * FormData/fetch bridge on this Expo SDK/React Native version combination,
 * not something specific to this app's code. expo-file-system's UploadTask
 * uses the platform's native upload APIs directly (NSURLSession on iOS,
 * OkHttp on Android) and does not go through that broken bridge at all, so
 * it works under the New Architecture without disabling it.
 */
export async function createScan(image: PickedImage): Promise<ScanOut> {
  const token = getAuthToken();
  const file = new File(image.uri);

  let result: { status: number; body: string };
  try {
    const task = new UploadTask(file, apiUrl('/api/scans'), {
      httpMethod: 'POST',
      uploadType: UploadType.MULTIPART,
      fieldName: 'file', // must match the backend's expected multipart field name exactly
      mimeType: image.mimeType,
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    result = await task.uploadAsync();
  } catch {
    // Per expo-file-system's docs, uploadAsync() rejects when the local file
    // can't be read or the request fails outright — either way, the photo
    // itself (not the server) is the actionable problem for the user.
    throw new PhotoUploadError();
  }

  if (result.status === 401) {
    notifyUnauthorized();
    throw new ApiError(401, 'Session expired');
  }

  if (result.status < 200 || result.status >= 300) {
    let detail = `Request failed (${result.status})`;
    try {
      const data = JSON.parse(result.body);
      if (typeof data?.detail === 'string') detail = data.detail;
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new ApiError(result.status, detail);
  }

  try {
    return JSON.parse(result.body) as ScanOut;
  } catch {
    throw new ApiError(result.status, 'The server returned an unreadable response.');
  }
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
