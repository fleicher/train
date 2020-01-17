import os
from typing import Set, Dict

import numpy as np
import pandas as pd

from claz.airport import Airport
from claz.util import get_eu_map, load_pickle, dump_pickle

COORDS_PICKLE = 'coords.pickle'
DATA_PICKLE = 'data/data_all.pickle'
DATA_DIR = 'data'
TIMES = ["2019Q2 ", "2019Q1 ", "2018Q4 ", "2018Q3 "]
LAT_RANGE = (35.0, 65.0)  # y-axis
LONG_RANGE = (-11.0, 39.0)  # x-axis


class Fly:
    def __init__(self, min_pas=None, *, renew=False):
        # code -> (lat, long, city, ctry)
        self.airport_coords = Fly._load_coords(renew=renew)
        # {airport_code1, airport_code2, ...}
        self.unknown_coords = set()

        # ['orig', 'dest', 'pas',
        #  "orig_lat", "orig_long", "orig_city", "orig_ctry",
        #  "dest_lat", "dest_long", "dest_city", "dest_ctry"]
        self.all_passenger_data = self._load_all_passenger_data(renew=renew)

        self.passenger_data: pd.DataFrame = pd.DataFrame()
        # ctry, city, code, lat, long
        self.airports: Dict[str, Airport] = {}
        if min_pas is not None:
            self.filter_passenger_data(min_pas)

    # NOTE: original file had missing entries for "ESDF", "ESMQ"
    @staticmethod
    def _load_coords(*, renew=False):
        if os.path.exists(COORDS_PICKLE) and not renew:
            return load_pickle(COORDS_PICKLE)
        coords = {}
        print("processing coords...")

        for _, row in pd.read_csv("icao/airport-codes.txt", delimiter=",").iterrows():
            lat, long = row.coordinates.replace('"', '').split(',')
            coords[row.ident] = (float(lat), float(long), row.municipality, row.iso_country)
        dump_pickle(COORDS_PICKLE, coords)
        return coords

    def _load_all_passenger_data(self, *, renew=False) -> pd.DataFrame:
        def retrieve_value(line):
            _, type_, route = line[0].split(',')
            country1, code1, country2, code2 = route.split("_")
            if type_ != "PAS_BRD":  # passengers boarding in both directions
                return pd.Series((None, None, None))
            for time in TIMES:
                try:
                    value = line[time]
                    if value.strip() == ":":
                        continue
                    return pd.Series((code1, code2, value))
                except KeyError:
                    continue
            return pd.Series((None, None, None))

        def add_coords(line: pd.Series):
            try:
                orig = self.airport_coords[line.orig]
                dest = self.airport_coords[line.dest]
            except KeyError:
                self.unknown_coords.add(line.orig)
                self.unknown_coords.add(line.dest)
                orig = (0, 0, None, None)
                dest = (0, 0, None, None)
            return line.append(pd.Series(orig + dest, index=[
                "orig_lat", "orig_long", "orig_city", "orig_ctry",
                "dest_lat", "dest_long", "dest_city", "dest_ctry"
            ]))  # lat is y-axis, long is x-axis, normal format: 50N, 10E

        columns = ['orig', 'dest', 'pas']

        if not renew and os.path.exists(DATA_PICKLE):
            return load_pickle(DATA_PICKLE)

        all_passenger_data = pd.DataFrame({name: [] for name in columns})
        for filename in [f for f in os.listdir(DATA_DIR) if f.endswith('.tsv')]:
            country_code = filename[-6:-4]
            print(country_code, "reading file:", filename)
            result = pd.read_csv(os.path.join(DATA_DIR, filename), delimiter='\t', encoding='utf-8')
            result = result.apply(retrieve_value, axis=1)
            result.columns = columns
            result = result.dropna()  # drop entries that are not in TIMES
            result.pas = result.pas.astype(int)
            all_passenger_data = all_passenger_data.append(result, ignore_index=True)

        print("start mapping coords to airport codes...")
        all_passenger_data = all_passenger_data.apply(add_coords, axis=1)

        dump_pickle(DATA_PICKLE, all_passenger_data)
        print("Saved passenger data to", DATA_PICKLE, "number of rows:", len(all_passenger_data))
        return all_passenger_data

    def filter_passenger_data(self, min_amount):
        print(f"start filtering of {len(self.all_passenger_data)} passenger data rows...")
        filtered_data = self.all_passenger_data[self.all_passenger_data.pas > min_amount]
        filtered_data = filtered_data[LAT_RANGE[0] < filtered_data.orig_lat]
        filtered_data = filtered_data[filtered_data.orig_lat < LAT_RANGE[1]]
        filtered_data = filtered_data[LONG_RANGE[0] < filtered_data.orig_long]
        filtered_data = filtered_data[filtered_data.orig_long < LONG_RANGE[1]]
        filtered_data = filtered_data[LAT_RANGE[0] < filtered_data.dest_lat]
        filtered_data = filtered_data[filtered_data.dest_lat < LAT_RANGE[1]]
        filtered_data = filtered_data[LONG_RANGE[0] < filtered_data.dest_long]
        filtered_data = filtered_data[filtered_data.dest_long < LONG_RANGE[1]]

        def extract_airports(line: pd.Series):
            return pd.Series((
                Airport(line.orig_ctry, line.orig_city, line.orig, line.orig_lat, line.orig_long),
                Airport(line.dest_ctry, line.dest_city, line.dest, line.dest_lat, line.dest_long),
                line.pas
            ), index=["orig_fly", "dest_fly", "pas"])

        self.passenger_data = filtered_data.apply(extract_airports, axis=1)
        airports_: Set[Airport] = set()
        airports_.update(list(self.passenger_data.orig_fly))
        airports_.update(list(self.passenger_data.dest_fly))
        self.airports = {airport.code: airport for airport in airports_}
        print(f"we have {len(self.passenger_data)} plane routes between {len(airports_)} European airports.")

    def draw_airports(self, draw_names=True, random_color=False, draw_lines=False):
        import cartopy.crs as ccrs
        import matplotlib.pyplot as plt

        ax, projection = get_eu_map(figsize=(30, 18))
        for airport_code, airport in self.airports.items():
            color = np.random.rand(3, ) if random_color else "gray"
            x, y = projection.transform_point(airport.long, airport.lat, ccrs.Geodetic())
            if draw_names:
                plt.plot(x, y, c=color)
                plt.text(x, y, s=airport.code, c=color)
            if draw_lines:
                pass
        plt.show()

        plt.savefig(os.path.join(DATA_DIR, "airports.png"))


if __name__ == "__main__":
    fly = Fly()
    fly.filter_passenger_data(30000)
