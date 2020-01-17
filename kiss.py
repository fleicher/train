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
                airport_codes = [airport_code for airport_code in mapping_corrections[station.code]]
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
            commentjson.dump({airport.code: station.code for airport, station in airport_to_station.items()}, f)

        for source, target, duration in self.rail.graph.edges.data('weight'):
            dist = Karte.distance(source.long, source.lat, target.long, target.lat)
            self.rail.graph[source][target]["dist"] = dist
            self.rail.graph[source][target]["speed"] = dist / duration

        return station_to_airports, airport_to_station

    @property
    def unmapped_stations(self):
        return [station for station in self.rail.stations.values() if station not in self.station_to_airports]

    def draw_mapping(self):
        import matplotlib.pyplot as plt
        from matplotlib.image import imread

        fig, ax = plt.subplots(figsize=(50, 25))
        #
        plt.imshow(imread('rail/High_Speed_Railroad_Map_of_Europe.png'),
                   extent=[0, 1037, 834 - 160, -160])
        for station, airports in self.station_to_airports.items():
            ax.text(station.x, station.y,
                    station.code + "\n".join(
                        ([] if len(airports) == 0 else [""]) + [airport.code for airport in airports]),
                    bbox={"facecolor": "white", "alpha": 0.5})
        plt.savefig("rails2fly.png")
        fig.show()

    UNMAPPED = "unmapped"
    NOT_IN_GRAPH = "not_in_graph"
    NO_RAIL = "no_rail"
    ISLAND = "island"
    NO_CONNECTION = "no_connection"
    TOO_LONG = "too_long"
    SHORT_ENOUGH = "short_enough"

    def calc_categorized_connections(self) -> pd.DataFrame:

        def find_route(line):
            index = ["orig_rail", "dest_rail", "duration", "route", "orig_err", "dest_err"]
            try:
                orig_station = self.airport_to_station[line.orig_fly]
                dest_station = self.airport_to_station[line.dest_fly]
            except KeyError:
                return line.append(pd.Series(
                    [None, None, None, None,
                     (Kiss.UNMAPPED if line.orig_fly not in self.airport_to_station else False),
                     (Kiss.UNMAPPED if line.dest_fly not in self.airport_to_station else False),
                     ], index=index
                ))
            try:
                duration, route = self.rail.travel_times[orig_station][dest_station]
            except KeyError:
                def return_line(is_orig: bool, is_dest: bool, value: str):
                    return line.append(pd.Series(
                        (orig_station, dest_station, None, None,
                         (value if is_orig else False),
                         (value if is_dest else False)),
                        index=index
                    ))
                if orig_station.type in ["N", "C"] or dest_station.type in ["N", "C"]:
                    return return_line(orig_station.type in ["N", "C"], dest_station.type in ["N", "C"], Kiss.NO_RAIL)
                if orig_station.type == "I" or dest_station.type == "I":
                    return return_line(orig_station.type == "I", dest_station.type == "I", Kiss.ISLAND)
                if not orig_station.in_graph or not dest_station.in_graph:
                    # this is the case if the connections json doesn't provide any data here
                    return return_line(not orig_station.in_graph, not dest_station.in_graph, Kiss.NOT_IN_GRAPH)

                return return_line(True, True, Kiss.NO_CONNECTION)
            return line.append(pd.Series(
                (orig_station, dest_station, duration, route, False, False), index=index
            ))

        passengers = self.fly.passenger_data
        print(f"analyzing the plane connections...")
        return passengers.apply(find_route, axis=1)

    @staticmethod
    def accum_pas(routes_):
        return "{:.1f}M".format(sum(routes_["pas"]) / 1000000)

    def statistics(self, *, show_where_to_add_data=False):
        routes = self.cat_routes.dropna()
        r = {
            "valid": routes,
            Kiss.SHORT_ENOUGH: routes[routes.duration <= self.max_duration],
            Kiss.TOO_LONG: routes[routes.duration > self.max_duration],
        }

        def sort_agg(df, mode_: str):
            return df.groupby(
                [f"orig_{mode_}"]).agg({'pas': ['sum', "mean", "count"]}).sort_values(("pas", "sum"), ascending=False)

        print(f"{len(self.cat_routes)} \t| {Kiss.accum_pas(self.cat_routes)} routes are categorized: ")
        descriptions = {
            Kiss.UNMAPPED: "no idea where the airport lies next to",
            Kiss.NO_RAIL: "we know there are no trains there",
            Kiss.ISLAND: "the flight goes to an island",
            Kiss.NOT_IN_GRAPH: ">= 1 station are not in graph",
            Kiss.NO_CONNECTION: "couldn't connect those two stations (Ireland)",
        }
        for err_type in [Kiss.UNMAPPED, Kiss.NO_RAIL, Kiss.ISLAND, Kiss.NOT_IN_GRAPH, Kiss.NO_CONNECTION]:
            r[err_type] = {
                "both": self.cat_routes[(self.cat_routes.orig_err == err_type) |
                                        (self.cat_routes.dest_err == err_type)],
                "orig": self.cat_routes[self.cat_routes.orig_err == err_type],
            }
            print(f"- {len(r[err_type]['both'])} \t| {Kiss.accum_pas(r[err_type]['both'])}:\t"
                  f" {descriptions[err_type]} ({err_type})")
            mode = 'fly' if err_type in [Kiss.UNMAPPED, Kiss.NO_RAIL, Kiss.ISLAND] else 'rail'
            self.cat_routes_split_sorted[err_type] = sort_agg(r[err_type]["orig"], mode)

        print("--------+---------")
        print(f"= {len(r['valid'])} \t| {Kiss.accum_pas(r['valid'])}:\t"
              f"have (possibly long) train connections")
        print(f"* {len(r[Kiss.SHORT_ENOUGH])} \t| {Kiss.accum_pas(r[Kiss.SHORT_ENOUGH])}:\t"
              f"convertible to (night) trains below {self.max_duration} mins")
        self.cat_routes_split_sorted[Kiss.TOO_LONG] = sort_agg(r[Kiss.TOO_LONG], "rail")

        if show_where_to_add_data:
            # print("These are the airports you should consider the most connecting to the railway network")
            # print(self.cat_routes_split_sorted[Kiss.UNMAPPED].head(10))
            print("These are the train stations that you should consider the most connecting.")
            print(self.cat_routes_split_sorted[Kiss.NOT_IN_GRAPH].head(10))

            print("These are the cities that cause most too long non-night-trainable flights")
            print(self.cat_routes_split_sorted[Kiss.TOO_LONG].head(20))

        return routes

    def histogram(self):
        buckets = {}
        for duration in range(100, 2100, 100):
            routes_bucket = self.routes[self.routes.duration <= duration]
            buckets[duration] = (
                len(routes_bucket),
                Kiss.accum_pas(routes_bucket)  # sum(routes_bucket.pas)
            )
        # hist = routes[["duration", "pas"]].hist()
        print(buckets)

    def draw(self):
        karte = Karte(figsize=(30, 18))
        for station, airports in self.station_to_airports.items():
            if station.in_graph:
                continue
            station.loc_mean(*zip([(airport.lat, airport.long) for airport in airports]))
            karte.point(station.lat, station.long, text=station.code)

        for source, target, duration in self.rail.graph.edges.data('weight'):
            dist = Karte.distance(source.long, source.lat, target.long, target.lat)
            self.rail.graph[source][target]["dist"] = dist
            self.rail.graph[source][target]["speed"] = dist / duration

        print("done")


if __name__ == "__main__":
    k = Kiss(Fly(1), Rail())
    print("done")
