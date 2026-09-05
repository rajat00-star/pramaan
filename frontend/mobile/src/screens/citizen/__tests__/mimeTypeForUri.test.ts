import { mimeTypeForUri } from '../ScanCaptureScreen';

// Regression coverage for iOS image-format handling (fix requirement #8):
// iOS commonly returns HEIC for library photos. Mislabeling a HEIC file as
// JPEG would let it reach the backend with a mismatched Content-Type,
// trading a clear "unsupported format" message for a confusing pipeline
// failure — so the fallback MIME detection must recognize it correctly.
describe('mimeTypeForUri', () => {
  it('detects HEIC', () => {
    expect(mimeTypeForUri('file:///tmp/IMG_1234.HEIC')).toBe('image/heic');
    expect(mimeTypeForUri('file:///tmp/img.heic')).toBe('image/heic');
  });

  it('detects HEIF', () => {
    expect(mimeTypeForUri('file:///tmp/img.heif')).toBe('image/heif');
  });

  it('detects PNG and WebP', () => {
    expect(mimeTypeForUri('file:///tmp/img.png')).toBe('image/png');
    expect(mimeTypeForUri('file:///tmp/img.webp')).toBe('image/webp');
  });

  it('defaults to JPEG for .jpg/.jpeg and anything unrecognized', () => {
    expect(mimeTypeForUri('file:///tmp/img.jpg')).toBe('image/jpeg');
    expect(mimeTypeForUri('file:///tmp/img.jpeg')).toBe('image/jpeg');
    expect(mimeTypeForUri('file:///tmp/img')).toBe('image/jpeg');
  });
});
