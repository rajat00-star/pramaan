class PramaanPipelineError(Exception):
    """Base class for pipeline errors that should be reported to the caller, not crash the request."""


class PramaanImageError(PramaanPipelineError):
    """Image could not be opened/decoded — corrupt file, unsupported format, zero-byte upload, etc."""


class PramaanOCRError(PramaanPipelineError):
    """The OCR engine itself failed (binary missing, language pack missing, decode error)."""
