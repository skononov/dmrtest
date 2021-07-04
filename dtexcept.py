
class DTError(Exception):
    def __init__(self, source=None, message=None):
        self.source = source
        self.message = message
        super().__init__((source+': ' if source else '') + (message if message else ''))


class DTInternalError(DTError):
    def __init__(self, source, message):
        super().__init__(source, message)


class DTComError(DTError):
    def __init__(self, message):
        super().__init__(None, message)


class DTUIError(DTError):
    def __init__(self, source=None, message=None):
        super().__init__(source, message)
