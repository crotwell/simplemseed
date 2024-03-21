

class CodecException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.name = "CodecException"

class SteimException(CodecException):
    def __init__(self, message):
        super().__init__(message)
        self.name = "SteimException"


class UnsupportedCompressionType(CodecException):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.name = "UnsupportedCompressionType"
