class DomainError(ValueError):
    def __init__(self, code: str, fields: tuple[dict[str, str], ...] = ()):
        super().__init__(code)
        self.code, self.fields = code, fields
