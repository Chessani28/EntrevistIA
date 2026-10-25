class AdmissionError(Exception):
    """Application-level error for admission simulator operations."""

    def __init__(self, code: str, message: str, status: int = 400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


# Backward-compatible alias for reusable modules that still reference the old name.
KnowledgeError = AdmissionError
