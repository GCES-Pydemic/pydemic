from collections import Mapping
from typing import Iterator, Type


class ParamsInfo(Mapping):
    """
    Object attached to WithParams subclasses that hold information about
    parameters.

    It behaves as a mapping from parameter names to their corresponding
    descriptors.
    """

    __slots__ = ("model", "primary", "alternative", "all")

    def __init__(self, cls: Type["WithParams"]):
        self.model = cls

        # Initialize parameter sets
        params = tuple(iter_params(self.model))
        self.primary = frozenset(k for k, v in params if not v.is_derived)
        self.alternative = frozenset(k for k, v in params if not v.is_derived)
        self.all = self.primary | self.alternative

    def __contains__(self, key):
        return key in self.all

    def __getitem__(self, item):
        if item in self.all:
            return getattr(self.model, item)
        raise KeyError(item)

    def __len__(self) -> int:
        return len(self.all)

    def __iter__(self):
        return iter(self.all)

    def is_static(self, param: str, obj: "WithParams"):
        """
        Return True if parameter is static.
        """
        return True


def iter_params(cls):
    """
    Iterate over all parameter descriptors in the given class.
    """
    for k in dir(cls):
        v = getattr(cls, k, None)
        if hasattr(v, "__get__") and getattr(v, "is_param", False):
            yield k, v
