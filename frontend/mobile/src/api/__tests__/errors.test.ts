import { ApiError, NetworkError, PhotoUploadError, friendlyErrorMessage } from '../errors';

describe('friendlyErrorMessage', () => {
  it('returns the PhotoUploadError message as-is (actionable: retake/reselect)', () => {
    expect(friendlyErrorMessage(new PhotoUploadError())).toMatch(/retake|different one/i);
  });

  it('returns the NetworkError message as-is', () => {
    expect(friendlyErrorMessage(new NetworkError())).toMatch(/reach the PraMaan server/i);
  });

  it('maps 415 to an unsupported-format message (relevant to HEIC uploads)', () => {
    expect(friendlyErrorMessage(new ApiError(415, 'nope'))).toMatch(/unsupported image format/i);
  });

  it('maps 401 to a session-expired message', () => {
    expect(friendlyErrorMessage(new ApiError(401, 'nope'))).toMatch(/session has expired/i);
  });
});
