from typing import List, Dict, Tuple

import commentjson
import networkx as nx

from claz.station import Station

TIMES_JSON = "rail/times.json"
TIMES_JSON2 = "rail/times2.json"


class Rail:
    def __init__(self):
        with open("rail/station_codes.json", "r") as f: # TODO: lost the x, y positions
            self.station_list: List[Station] = [Station(station_name, station_code)
                                                for station_name, station_code in commentjson.load(f).items()]
        self.stations: Dict[str, Station] = {station.code: station for station in self.station_list if
                                             station.code is not None}
        self.graph: nx.Graph = self.create_network()
        self.travel_times: Dict[Station, Dict[Station, Tuple[int, List[Station]]]] = self.calc_travel_times()

    # @staticmethod
    # def read_stations_old(*, renew=False):
    #     from claz.util import load_pickle, dump_pickle
    #     STATIONS_PICKLE = 'rail/stations.pickle'
    #     if os.path.exists(STATIONS_PICKLE) and not renew:
    #         stations = load_pickle(STATIONS_PICKLE)
    #         return sorted(stations, key=lambda c: c.x)
    #
    #     xmldoc = minidom.parse('rail/High_Speed_Railroad_Map_of_Europe.svg')
    #     itemlist = xmldoc.getElementsByTagName('text')
    #     # print("got", len(itemlist), "text tags.")
    #     fixes = {
    #         "Santiago de ": "Santiago de Comp.",
    #         "Santiago": None,
    #         "Bruxelles/Brussel": "Brussel",
    #         "Dortm.": "Dortmund",
    #         "Nizhny ": "Nizhny Novgorod",
    #         "Novgorod": None,
    #     }
    #     stations = []
    #     for item in itemlist:
    #         if item.firstChild is not None and item.firstChild.firstChild is not None:
    #             tspan = item.firstChild  # potentially there are two?
    #             name = tspan.firstChild.nodeValue
    #             if name == "Legend :":
    #                 break  # the legend box is on the bottom of the svg file.
    #             if name in fixes:
    #                 if fixes[name] is None:
    #                     continue
    #                 name = fixes[name]
    #             stations.append(Station(name,
    #                                     tspan.getAttribute("x"),
    #                                     tspan.getAttribute("y")))
    #     stations.sort(key=lambda c: c.x)
    #     # TODO: bad but unfortunately now important, they have to be ordered this way
    #     # TODO: before the codes are created!
    #     # map "munchen" (from München) -> "mun" (first three chars)
    #     codes_set = set()
    #     for station in stations:
    #         for counter in range(2, len(station.simple_name)):
    #             code = station.simple_name[0:2] + station.simple_name[counter]
    #             if code not in codes_set:
    #                 break
    #         else:
    #             for counter in range(3, len(station.simple_name)):
    #                 code = station.simple_name[0] + station.simple_name[2] + station.simple_name[counter]
    #                 if code not in codes_set:
    #                     break
    #             else:
    #                 assert False, f"had trouble finding a name for {station}"
    #         station.code = code
    #
    #     dump_pickle(STATIONS_PICKLE, stations)
    #     return {station.code: station for station in stations}

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
            return self.stations[u], self.stations[v], int(w // 1 * 60 + w % 1 * 100)

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
        for source_station, targets in nx.shortest_path(self.graph, weight="weight").items():
            targets2 = {}
            for target_station, route in targets.items():
                length = sum([self.graph[route[n]][route[n + 1]]["weight"]
                              for n in range(len(route) - 1)])
                targets2[target_station] = (length, route)
            times[source_station] = targets2
        return times



if __name__ == "__main__":
    r = Rail()
