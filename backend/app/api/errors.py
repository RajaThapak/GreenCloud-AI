class ApiError(Exception):
    def __init__(self, status: int, detail: str, code: str = "error"):
        self.status, self.detail, self.code = status, detail, code
