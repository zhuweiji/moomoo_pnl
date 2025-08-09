import abc
import threading
from typing import Type


class Singleton(type):
    """Thread-safe singleton metaclass

    Usage:
    ```
    class MyClass(BaseClass, metaclass=Singleton):
        pass
    ```
    """

    _instances: dict[Type, object] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # Double-checked locking pattern
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ABCSingletonMeta(abc.ABCMeta, Singleton):
    """Thread-safe singleton metaclass

    Usage:
    ```
    class MyClass(SomeAbstractClass, metaclass=ABCSingletonMeta):
        pass
    ```
    """

    pass
