/**
 * Regression tests for the physical-iOS scan-upload fix.
 *
 * Root cause (confirmed via a live device diagnostic, not guessed): on a
 * physical iPhone, fetch()'s FormData implementation rejected every
 * multipart image upload with `Error: Unsupported FormDataPart
 * implementation` before any request reached the network — Docker's access
 * logs showed zero incoming requests. createScan() now uses
 * expo-file-system's native UploadTask instead of fetch()+FormData. These
 * tests lock in the exact request contract the backend requires (field name
 * `file`, POST, multipart) and the error-mapping behavior, using a mocked
 * expo-file-system — they cannot exercise the real native networking code,
 * which was instead verified on an actual device (see PR/report).
 */
import { UploadType } from 'expo-file-system';

import { getAuthToken, registerUnauthorizedHandler, setAuthToken } from '../client';
import { ApiError, PhotoUploadError } from '../errors';
import { createScan } from '../scans';

jest.mock('expo-file-system', () => ({
  File: jest.fn().mockImplementation((uri: string) => ({ uri })),
  UploadTask: jest.fn(),
  UploadType: { BINARY_CONTENT: 0, MULTIPART: 1 },
}));

const MockedUploadTask = jest.requireMock('expo-file-system').UploadTask as jest.Mock;

const image = { uri: 'file:///var/mobile/tmp/photo.jpg', fileName: 'scan-123.jpg', mimeType: 'image/jpeg' };

function mockUploadResolves(result: { status: number; body: string }) {
  MockedUploadTask.mockImplementation(() => ({
    uploadAsync: jest.fn().mockResolvedValue(result),
  }));
}

function mockUploadRejects() {
  MockedUploadTask.mockImplementation(() => ({
    uploadAsync: jest.fn().mockRejectedValue(new Error('native upload failure: file could not be read')),
  }));
}

describe('createScan (physical-device upload path)', () => {
  beforeEach(() => {
    MockedUploadTask.mockReset();
    setAuthToken(null);
    registerUnauthorizedHandler(() => {});
  });

  it('uploads with fieldName "file" — the exact contract the backend requires', async () => {
    mockUploadResolves({ status: 201, body: JSON.stringify({ id: 'scan-1' }) });
    setAuthToken('test-token-123');

    await createScan(image);

    expect(MockedUploadTask).toHaveBeenCalledTimes(1);
    const [fileArg, urlArg, optionsArg] = MockedUploadTask.mock.calls[0];
    expect(fileArg).toEqual({ uri: image.uri });
    expect(urlArg).toMatch(/\/api\/scans$/);
    expect(optionsArg).toMatchObject({
      httpMethod: 'POST',
      uploadType: UploadType.MULTIPART,
      fieldName: 'file',
      mimeType: 'image/jpeg',
      headers: { Authorization: 'Bearer test-token-123' },
    });
  });

  it('omits the Authorization header when there is no token, and never logs the token', async () => {
    mockUploadResolves({ status: 201, body: JSON.stringify({ id: 'scan-1' }) });
    const logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

    await createScan(image);

    const optionsArg = MockedUploadTask.mock.calls[0][2];
    expect(optionsArg.headers).toBeUndefined();
    expect(logSpy).not.toHaveBeenCalled(); // no diagnostic logging left behind
    logSpy.mockRestore();
  });

  it('resolves with the parsed scan on a 2xx response', async () => {
    mockUploadResolves({ status: 201, body: JSON.stringify({ id: 'scan-1', overall_verdict: 'REVIEW' }) });
    await expect(createScan(image)).resolves.toEqual({ id: 'scan-1', overall_verdict: 'REVIEW' });
  });

  it('throws ApiError carrying the backend detail on a non-2xx response', async () => {
    mockUploadResolves({ status: 415, body: JSON.stringify({ detail: 'Unsupported content type' }) });
    await expect(createScan(image)).rejects.toMatchObject(
      new ApiError(415, 'Unsupported content type')
    );
  });

  it('notifies the unauthorized handler and throws ApiError on a 401 response', async () => {
    const handler = jest.fn();
    registerUnauthorizedHandler(handler);
    mockUploadResolves({ status: 401, body: JSON.stringify({ detail: 'Session expired' }) });

    await expect(createScan(image)).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('throws PhotoUploadError — not a generic network error — when the native task rejects (unreadable local file)', async () => {
    mockUploadRejects();
    await expect(createScan(image)).rejects.toBeInstanceOf(PhotoUploadError);
  });

  it('getAuthToken reflects the token actually used for the upload', async () => {
    setAuthToken('abc');
    expect(getAuthToken()).toBe('abc');
  });
});
