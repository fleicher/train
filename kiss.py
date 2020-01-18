from typing import Dict, List

import commentjson
import pandas as pd

from claz.airport import Airport
from claz.station import Station
from claz.util import Karte
from fly import Fly
from rail import Rail


class Kiss:
    def __init__(self, fly: Fly, rail: Rail, max_duration=900):
        self.fly = fly
        self.rail = rail
        self.max_duration = max_duration
        self.station_to_airports, self.airport_to_station = self._map_station_airport()
        self.add_distance_data_to_rail_graph()

        self.cat_routes = self.calc_categorized_connections()
        self.cat_routes_split_sorted: Dict[str, pd.DataFrame] = {}
        self.routes: pd.DataFrame = self.statistics()

    def _map_station_airport(self):
        airports_by_simple_name: Dict[str, List[Airport]] = {}
        for airport in self.fly.airports.values():
            if airport.simple_name not in airports_by_simple_name:
                airports_by_simple_name[airport.simple_name] = []
            airports_by_simple_name[airport.simple_name].append(airport)

        with open("rail/mapping_names.json", "r") as f:
            mapping_corrections: Dict[str, List[str]] = commentjson.load(f)

        station_to_airports: Dict[Station, List[Airport]] = {}
        for station in self.rail.station_list:
            if station.code in mapping_corrections:
                airport_codes = [airport_code for airport_code
                                 in mapping_corrections[station.code]]
                station_to_airports[station] = []
                for airport_code in airport_codes:
                    try:
                        station_to_airports[station].append(self.fly.airports[airport_code])
                    except KeyError:
                        continue  # this Airport was not important enough to make the cut.
            elif station.simple_name in airports_by_simple_name:
                station_to_airports[station] = airports_by_simple_name[station.simple_name]
            else:
                station_to_airports[station] = []
        airport_to_station: Dict[Airport, Station] = {
            airport: station
            for station, airports in station_to_airports.items()
            for airport in airports
        }
        with open("airport2station.json", "w") as f:
            commentjson.dump({airport.code: station.code for airport, station
                              in airport_to_station.items()}, f)

        return station_to_airports, airport_to_station

    @property
    def present_station_to_airports(self):
        return [(station, airports) for station, airports
                in self.station_to_airports.items() if station.in_graph]

    def add_distance_data_to_rail_graph(self):
        no_airport_coords = {
            "aar": (56.162939, 10.203921),
            "ant": (51.2194475, 4.4024643),
            "bia": (53.1324886, 23.1688403),
            "dau": (55.88333, 26.53333),
            "mah": (49.4874592, 8.4660395),
            "brs": (52.097622, 23.734051)
        }
        for station, airports in self.present_station_to_airports:
            if station.code in no_airport_coords:
                station.lat, station.long = no_airport_coords[station.code]
            else:
                lats, longs = list(zip(*[(airport.lat, airport.long) for airport in airports]))
                station.loc_mean(lats, longs)

        for source_code, target_code, duration in self.rail.graph.edges.data('weight'):
            source, target = self.rail.stations[source_code], self.rail.stations[target_code]
            dist = Karte.distance(source.lat, source.long, target.lat, target.long)
            self.rail.graph[source_code][target_code]["dist"] = dist
            self.rail.graph[source_code][target_code]["speed"] = dist / 1000 / duration * 60

    @property
    def unmapped_stations(self):
        return [station for station in self.rail.stations.values()
                if station not in self.station_to_airports]

    UNMAPPED = "unmapped"
    NOT_IN_GRAPH = "not_in_graph"
    NO_RAIL = "no_rail"
    ISLAND = "island"
    NO_CONNECTION = "no_connection"
    TOO_LONG = "too_long"
    SHORT_ENOUGH = "short_enough"

    def calc_categorized_connections(self) -> pd.DataFrame:

        def find_route(line):
            index = ["orig_rail", "dest_rail", "dur_rail", "speed_rail", "route",
                     "orig_err", "dest_err"]
            orig_station, dest_station = None, None

            def error_line(is_orig: bool, is_dest: bool, value: str):
                return line.append(pd.Series(
                    (orig_station, dest_station, None, None, None,
                     (value if is_orig else False),
                     (value if is_dest else False)),
                    index=index
                ))

            try:
                orig_station = self.airport_to_station[line.orig_fly]
                dest_station = self.airport_to_station[line.dest_fly]
            except KeyError:
                return error_line(
                    line.orig_fly not in self.airport_to_station,
                    line.dest_fly not in self.airport_to_station, Kiss.UNMAPPED)
            try:
                duration, route = self.rail.travel_times[orig_station][dest_station]
                # duration is in min, dist in meters, speed in km/h
                speed = line.dist_fly / 1000 / duration * 60
            except KeyError:
                if orig_station.type in ["N", "C"] or dest_station.type in ["N", "C"]:
                    return error_line(orig_station.type in ["N", "C"],
                                      dest_station.type in ["N", "C"], Kiss.NO_RAIL)
                if orig_station.type == "I" or dest_station.type == "I":
                    return error_line(orig_station.type == "I",
                                      dest_station.type == "I", Kiss.ISLAND)
                if not orig_station.in_graph or not dest_station.in_graph:
                    # this is the case if the connections json doesn't provide any data here
                    return error_line(not orig_station.in_graph,
                                      not dest_station.in_graph, Kiss.NOT_IN_GRAPH)

                return error_line(True, True, Kiss.NO_CONNECTION)
            return line.append(pd.Series(
                (orig_station, dest_station, duration, speed, route, False, False), index=index
            ))

        passengers = self.fly.passenger_data
        print(f"analyzing the plane connections...")
        return passengers.apply(find_route, axis=1)

    @staticmethod
    def accumulate_pas(routes_):
        return "{:.1f}M".format(sum(routes_["pas"]) / 1000000)

    def statistics(self, *, show_where_to_add_data=False):
        routes = self.cat_routes.dropna()
        r = {
            "valid": routes,
            Kiss.SHORT_ENOUGH: routes[routes.dur_rail <= self.max_duration],
            Kiss.TOO_LONG: routes[routes.dur_rail > self.max_duration],
        }

        def sort_agg(df, mode_: str):
            return df.groupby(
                [f"orig_{mode_}"]).agg({'pas': ['sum', "mean", "count"]}).sort_values(
                ("pas", "sum"), ascending=False)

        print(f"{len(self.cat_routes)} \t| {Kiss.accumulate_pas(self.cat_routes)} categorized: ")
        descriptions = {
            Kiss.UNMAPPED: "no idea where the airport lies next to",
            Kiss.NO_RAIL: "we know there are no trains there",
            Kiss.ISLAND: "the flight goes to an island",
            Kiss.NOT_IN_GRAPH: ">= 1 station are not in graph",
            Kiss.NO_CONNECTION: "couldn't connect those two stations (Ireland)",
        }
        for err_type in [Kiss.UNMAPPED, Kiss.NO_RAIL, Kiss.ISLAND,
                         Kiss.NOT_IN_GRAPH, Kiss.NO_CONNECTION]:
            r[err_type] = {
                "both": self.cat_routes[(self.cat_routes.orig_err == err_type) |
                                        (self.cat_routes.dest_err == err_type)],
                "orig": self.cat_routes[self.cat_routes.orig_err == err_type],
            }
            print(f"- {len(r[err_type]['both'])} \t| {Kiss.accumulate_pas(r[err_type]['both'])}:\t"
                  f" {descriptions[err_type]} ({err_type})")
            mode = 'fly' if err_type in [Kiss.UNMAPPED, Kiss.NO_RAIL, Kiss.ISLAND] else 'rail'
            self.cat_routes_split_sorted[err_type] = sort_agg(r[err_type]["orig"], mode)

        print("--------+---------")
        print(f"= {len(r['valid'])} \t| {Kiss.accumulate_pas(r['valid'])}:\t"
              f"have (possibly long) train connections")
        print(f"* {len(r[Kiss.SHORT_ENOUGH])} \t| {Kiss.accumulate_pas(r[Kiss.SHORT_ENOUGH])}:\t"
              f"convertible to (night) trains below {self.max_duration} min")
        self.cat_routes_split_sorted[Kiss.TOO_LONG] = sort_agg(r[Kiss.TOO_LONG], "rail")

        if show_where_to_add_data:
            # print("These are the airports you should consider the most"
            #       "connecting to the railway network")
            # print(self.cat_routes_split_sorted[Kiss.UNMAPPED].head(10))
            print("These are the train stations that you should consider the most connecting.")
            print(self.cat_routes_split_sorted[Kiss.NOT_IN_GRAPH].head(10))

            print("These are the cities that cause most too long non-night-trainable flights")
            print(self.cat_routes_split_sorted[Kiss.TOO_LONG].head(20))
        return routes

    def times_comparison(self):
        buckets = {}
        for duration in range(100, 2100, 100):
            routes_bucket = self.routes[self.routes.dur_rail <= duration]
            buckets[duration] = (
                len(routes_bucket),
                Kiss.accumulate_pas(routes_bucket)  # sum(routes_bucket.pas)
            )
        # hist = routes[["dur_rail", "pas"]].hist()
        print(buckets)

        def add_dur_difs(line):
            return line.append(pd.Series([
                round(line.dur_rail / line.dur_fly, 2),
                line.dur_rail - line.dur_fly,
            ], index=["dur_dif_prop", "dur_dif_abs"]))

        dur_difs: pd.DataFrame = self.routes.apply(add_dur_difs, axis=1)
        dur = {
            "most_prop": dur_difs.sort_values("dur_dif_prop")
        }

    def draw(self):
        karte = Karte(figsize=(8, 6))
        for station, airports in self.present_station_to_airports:
            karte.point(station.lat, station.long, text=station.code)

        speeds = []
        lat1s, long1s, lat2s, long2s = [], [], [], []
        for source_code, target_code, speed in self.rail.graph.edges.data('speed'):
            source = self.rail.stations[source_code]
            target = self.rail.stations[target_code]
            lat1s.append(source.lat)
            long1s.append(source.long)
            lat2s.append(target.lat)
            long2s.append(target.long)
            speeds.append(speed)
        karte.lines(lat1s, long1s, lat2s, long2s,
                    colors=Karte.color_list(speeds, min_=50, max_=170))
        karte.show()
        print("done")


if __name__ == "__main__":
    k = Kiss(Fly(1), Rail())
    k.draw()
    k.times_comparison()
    print("done")
