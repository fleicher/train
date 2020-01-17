from typing import Union, Optional, List
import numpy as np

from claz.util import to_ascii

StatCode = Union["Station", str]


class Station:
    def __init__(self, name, code=None):
        self.name = name
        self.simple_name = to_ascii(name)
        assert len(self.simple_name) >= 3
        if code in ["I", "N", "C"]:
            self.code = self.simple_name
            self.type = code
        else:
            self.code = code
            self.type = "R"
        self.in_graph = None

        self.lat: Optional[float] = None
        self.long: Optional[float] = None

    @staticmethod
    def _get_station_code(other: StatCode):
        return str if isinstance(other, str) else other.code

    def loc_mean(self, lat: List[float], long: List[float]):
        self.lat = np.mean(lat)
        self.long = np.mean(long)

    def __str__(self):
        return f"{self.code}({self.name})"

    def __repr__(self):
        return str(self)

    def __eq__(self, other: StatCode):
        return self.code == Station._get_station_code(other)

    def __ne__(self, other: StatCode):
        return self.code != Station._get_station_code(other)

    def __gt__(self, other: StatCode):
        return self.code > Station._get_station_code(other)

    def __ge__(self, other: StatCode):
        return self.code >= Station._get_station_code(other)

    def __lt__(self, other: StatCode):
        return self.code < Station._get_station_code(other)

    def __le__(self, other: StatCode):
        return self.code <= Station._get_station_code(other)

    def __hash__(self):
        if self.code is None:
            raise ValueError("You need to set the Station's code first")
        return hash(self.code)
