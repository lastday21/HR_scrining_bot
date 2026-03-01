class ValidationError(ValueError):
    pass


class RedisStorageError(RuntimeError):
    pass


class LlmRequestError(RuntimeError):
    pass


class SheetsWriteError(RuntimeError):
    pass
