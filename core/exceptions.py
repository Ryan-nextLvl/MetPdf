class Any2PDFError(Exception):
    pass


class UnsupportedFormatError(Any2PDFError):
    def __init__(self, ext: str):
        super().__init__(f"Unsupported file format: '{ext}'")
        self.ext = ext


class ConversionError(Any2PDFError):
    def __init__(self, path: str, reason: str):
        super().__init__(f"Failed to convert '{path}': {reason}")
        self.path = path
        self.reason = reason


class InputFileNotFoundError(Any2PDFError):
    def __init__(self, path: str):
        super().__init__(f"Input file not found: '{path}'")
        self.path = path
