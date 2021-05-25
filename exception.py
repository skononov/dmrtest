
class DTError(Exception):
    def __init__(self, source, message):
        super().__init__(source+': '+message)
        
class DTInternalError(DTError):
    def __init__(self, source, message):
        super().__init__(source, message)

class DTComError(DTError):
    def __init__(self, source, message):
        super().__init__(source, message)

class DTUIError(DTError):
    def __init__(self, source, message):
        super().__init__(source, message)
