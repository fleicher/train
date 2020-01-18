from typing import List, Dict, Tuple

import commentjson
import networkx as nx
import pandas as pd

from claz.station import Station

TIMES_JSON = "rail/times.json"
TIMES_JSON2 = "rail/times2.json"


class Rail:
    DURATION = "weight"

    def __init__(self):
        with open("rail/station_codes.json", "r") as f:
            self.station_list: List[Station] = [Station(station_name, station_code)
                                                for station_name, station_code in
                                                commentjson.load(f).items()]
        self.stations: Dict[str, Station] = {station.code: station for station in self.station_list
                                             if station.code is not None}
        self.graph: nx.Graph = self.create_network()
        self.travel_times: Dict[
            Station, Dict[Station, Tuple[int, List[Station]]]] = self.calc_travel_times()
        self.unnecessary_links = self.find_unnecessary_links(remove=True)

    def create_network(self) -> nx.Graph:
        graph = nx.Graph()
        with open(TIMES_JSON, "r") as f:
            travel_times = commentjson.load(f)["times"]
            # [
            #   ["bel", "dub", 2.10],
            #   ["dub", "cok", 2.45],
            #           ...
            # ]
        with open(TIMES_JSON2, "r") as f:
            travel_times = travel_times + commentjson.load(f)["times"]

        # this is necessary, because the json files store the travel durations as
        # 2.45 -> 2 hrs 45 mins
        def to_minutes(uvw):
            u, v, w = uvw
            return u, v, int(w // 1 * 60 + w % 1 * 100)

        times_in_mins = [to_minutes(time) for time in travel_times]
        graph.add_weighted_edges_from(times_in_mins)

        stations_in_the_graph = list(nx.nodes(graph))
        number_of_stations_in_graph = 0
        for station_code, station in self.stations.items():
            station.in_graph = station_code in stations_in_the_graph
            number_of_stations_in_graph += int(station.in_graph)
        print(f"{number_of_stations_in_graph} of {len(self.stations)} train stations "
              f"are added to the graph.")
        return graph

    def connected_components(self):
        return nx.connected_components(self.graph)

    def calc_travel_times(self):
        times: Dict[Station, Dict[Station, Tuple[int, List[Station]]]] = {}
        # print("getting rail graph network lengths...")
        for source_code, targets in nx.shortest_path(self.graph, weight=Rail.DURATION).items():
            targets2 = {}
            for target_code, route in targets.items():
                length = sum([self.graph[route[n]][route[n + 1]][Rail.DURATION]
                              for n in range(len(route) - 1)])
                targets2[self.stations[target_code]] = (length, route)
            times[self.stations[source_code]] = targets2
        return times

    def find_unnecessary_links(self, remove=True):
        columns = ["source", "target", "dur_short", "dur_dir", "prop_longer", "route"]
        useless_links: List[Tuple[Station, Station, float, float, float, List[Station]]] = []
        # unnecessary_links: List[Tuple[Station, Station, float, float, float, List[Station]]] = []

        for source, targets in self.travel_times.items():
            source_neighbors: Dict[str, Dict[str, float]] = dict(self.graph[source.code])
            for target, (shortest_duration, route) in targets.items():
                if len(route) < 3 or target.code not in source_neighbors:
                    continue  # a direct route has 2 elements: [source, target]
                direct_duration = source_neighbors[target.code][Rail.DURATION]
                link = (source, target, shortest_duration, direct_duration,
                        direct_duration / shortest_duration, route)
                if direct_duration > shortest_duration:
                    useless_links.append(link)
                    if remove:
                        self.graph.remove_edge(source.code, target.code)
        if remove:
            print(f"Eliminated {len(useless_links)} direct links from the graph"
                  f"that have shorter alternatives")
        return pd.DataFrame(useless_links, columns=columns).sort_values(
            "prop_longer", ascending=False)


if __name__ == "__main__":
    r = Rail()
