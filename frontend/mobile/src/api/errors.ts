/** Typed error thrown by the API client — never a raw stack trace shown to the user. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message = 'Could not reach the PraMaan server. Check your connection and try again.') {
    super(message);
    this.name = 'NetworkError';
  }
}

/** Maps a backend HTTP status + optional detail message to a short, safe,
 * user-facing message. Never surfaces raw exception text or stack traces. */
export function friendlyErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) return err.message;
  if (err instanceof ApiError) {
    switch (err.status) {
      case 401:
        return 'Your session has expired. Please sign in again.';
      case 403:
        return "You don't have permission to do that.";
      case 404:
        return 'Not found.';
      case 413:
        return 'That image is too large. Please choose a smaller photo.';
      case 415:
        return 'Unsupported image format. Please use JPEG, PNG, or WebP.';
      case 422:
        return err.detail || 'That request could not be processed.';
      case 500:
      case 502:
      case 503:
        return 'The PraMaan server is temporarily unavailable. Please try again shortly.';
      default:
        return err.detail || 'Something went wrong. Please try again.';
    }
  }
  return 'Something went wrong. Please try again.';
}
