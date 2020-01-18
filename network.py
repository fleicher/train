import pickle

import commentjson
import networkx as nx
import pandas as pd

G = nx.Graph()


def create_network():
    with open("rail/times.json", "r") as f:
        times = commentjson.load(f)

    def to_minutes(uvw):
        u, v, w = uvw
        return u, v, int(w // 1 * 60 + w % 1 * 100)

    times_in_mins = [to_minutes(time) for time in times["times"]]
    G.add_weighted_edges_from(times_in_mins)
    print(G.edges.data('weight'))


def draw_network():
    nx.draw_shell(G, with_labels=True)


def get_lengths():
    times = {}
    print("getting network lengths...")
    for source, targets in nx.shortest_path(G, weight="weight").items():
        targets2 = {}
        for target, route in targets.items():
            length = sum([G[route[n]][route[n+1]]["weight"]
                          for n in range(len(route)-1)])
            targets2[target] = (length, route)
        times[source] = targets2
    return times


def read_passengers() -> pd.DataFrame:
    data_file = "data/data.pickle"
    with open(data_file, 'rb') as h:
        data_ = pickle.load(h)
        print("loaded passenger data from", data_file, "loaded rows:", len(data_))
        return data_


def read_mapping():
    with open("rail/links_temp.json") as f:
        return commentjson.load(f)


def reverse_mapping(mapping):
    reverse = {}
    print("calculating reverse map...")
    for rail, info in mapping.items():
        for fly in info["codes"]:
            reverse[fly] = rail
    return reverse


def find_suitable_routes(network, mapping, passengers):
    def find_route(line):
        index = ["orig_rail", "dest_rail", "duration", "route"]
        try:
            orig = mapping[line.orig]  # train <= plane mapping
            dest = mapping[line.dest]
            duration, route = network[orig][dest]
        except KeyError:
            return pd.Series(
                [None] * (len(line) + 4),
                index=list(line.index) + index
            )
        return line.append(pd.Series(
            (orig, dest, duration, route), index=index
        ))
    print(f"finding suitable train connections for {len(passengers)} plane routes")
    passengers2 = passengers.apply(find_route, axis=1)
    return passengers2.dropna()


if __name__ == "__main__":
    limit = 900  # in min
    create_network()
    # draw_network()
    net = get_lengths()
    pas = read_passengers()
    mra = read_mapping()
    mar = reverse_mapping(mra)
    data = find_suitable_routes(net, mar, pas)
    data2 = data[data.duration <= limit].sort_values("pas", ascending=False)
    print(f"from {len(data)} plane routes, {len(data2)} can be done in under {limit} mins")
    print("done")
