from claz.util import to_ascii


class Airport:
    missing_names = []

    def __init__(self, ctry_: str, city_: str, code_: str, lat_: float, long_: float):
        self.ctry = ctry_
        self.city = city_
        self.code = code_
        self.lat = lat_
        self.long = long_
        try:
            self.simple_name = to_ascii(city_[:city_.index("/")])
        except ValueError:
            self.simple_name = to_ascii(city_)
        try:
            self.simple_name = to_ascii(self.simple_name[:self.simple_name.index("(")]).strip()
        except ValueError:
            pass
        except AttributeError:
            # TODO: this is only because I am tired.
            Airport.missing_names.append(code_)
            self.city = code_
            self.simple_name = code_

    def __str__(self):
        return f"{self.code}:{self.city}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other: "Airport"):
        return self.code == other.code

    def __ne__(self, other: "Airport"):
        return self.code != other.code

    def __gt__(self, other: "Airport"):
        return self.code > other.code

    def __ge__(self, other: "Airport"):
        return self.code >= other.code

    def __lt__(self, other: "Airport"):
        return self.code < other.code

    def __le__(self, other: "Airport"):
        return self.code <= other.code

    def __hash__(self):
        return hash(self.code)