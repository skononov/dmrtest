
class Singleton(type):
    """
    Metaclass for defining singleton classes
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

#Use in Python3
##class MyClass(BaseClass, metaclass=Singleton):
##   pass

