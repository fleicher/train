import os
import pickle
from typing import List

import numpy as np
import unidecode

import matplotlib.pyplot as plt
import matplotlib.patches as m_patches
import cartopy.crs as c_crs
import cartopy.feature
from pyproj import Geod

LAT_RANGE = (35.0, 65.0)  # y-axis
LONG_RANGE = (-11.0, 39.0)  # x-axis


def get_eu_map(figsize=(10, 6)):

    projection = c_crs.AlbersEqualArea(np.mean(LONG_RANGE), np.mean(LAT_RANGE))
    plt.figure(figsize=figsize)
    ax = plt.axes(projection=projection)
    ax.set_extent(LONG_RANGE + LAT_RANGE)

    ax.add_feature(cartopy.feature.OCEAN)
    ax.add_feature(cartopy.feature.LAND, edgecolor='black')
    ax.add_feature(cartopy.feature.LAKES, edgecolor='black')
    return ax, projection


def to_ascii(name):
    if name != name:  # nan
        return ""
    return unidecode.unidecode(name).lower().translate(
        {ord(ch): '' for ch in ["'", "-", ".", " "]})


def load_pickle(file_path):
    # print("loading pickle codes from", os.path.join(os.getcwd(), file_path))
    with open(file_path, 'rb') as handle:
        return pickle.load(handle)


def dump_pickle(file_path, data):
    print("storing pickle to", os.path.join(os.getcwd(), file_path))
    with open(file_path, 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


class Karte:
    g = Geod(ellps='WGS84')
    cm = plt.cm.jet

    def __init__(self, figsize=(10, 6)):
        self.projection = c_crs.AlbersEqualArea(np.mean(LONG_RANGE), np.mean(LAT_RANGE))
        plt.figure(figsize=figsize)
        self.ax = plt.axes(projection=self.projection)
        self.ax.set_extent(LONG_RANGE + LAT_RANGE)

        self.ax.add_feature(cartopy.feature.OCEAN)
        self.ax.add_feature(cartopy.feature.LAND, edgecolor='black')
        self.ax.add_feature(cartopy.feature.LAKES, edgecolor='black')

    def point(self, lat, long, text=None, color="black"):
        x, y = self.projection.transform_point(long, lat, c_crs.Geodetic())
        plt.plot(x, y, c=color)
        if text is not None:
            plt.text(x, y, s=text, c=color)

    def line(self, lat1: float, long1: float, lat2: float, long2: float, *, color="black"):
        x1, y1 = self.projection.transform_point(long1, lat1, c_crs.Geodetic())
        x2, y2 = self.projection.transform_point(long2, lat2, c_crs.Geodetic())
        plt.plot([x1, x2], [y1, y2], c=color)

    def lines(self, lat1s: List[float], long1s: List[float],
              lat2s: List[float], long2s: List[float], colors: List[str] = None):

        xyz_1 = self.projection.transform_points(c_crs.Geodetic(),
                                                 np.array(long1s), np.array(lat1s))
        xyz_2 = self.projection.transform_points(c_crs.Geodetic(),
                                                 np.array(long2s), np.array(lat2s))
        xs = np.hstack((xyz_1[:, 0].reshape((-1, 1)), xyz_2[:, 0].reshape((-1, 1))))
        ys = np.hstack((xyz_1[:, 1].reshape((-1, 1)), xyz_2[:, 1].reshape((-1, 1))))
        # this has the form: [[x11, x12], [x21, x22], ...]

        # to plot multiple lines simultaneously, the input needs to be in the format
        # plot([x11, x12], [y11, y12], [x21, x22], [y21, y22], [x31, x32], [y31, y32], ... )
        drawn_lines_unflat = [(xs[i], ys[i], ("k-" if colors is None else colors[i])) for i in
                              range(len(xs))]
        self.ax.plot(*[el for line in drawn_lines_unflat for el in line])

    @staticmethod
    def show():
        plt.show()

    @staticmethod
    def color(value, rng=(0, 250)):
        return Karte.cm((value-rng[0]) / (rng[1]-rng[0]))

    @staticmethod
    def color_list(weights: List[float], *, min_: float, max_: float):
        li = ['k', 'r', 'y', 'g', 'c', 'b', 'm']
        bounds = np.linspace(min_, max_, len(li)-1)
        patches = [
            m_patches.Patch(color=li[i], label=f"<{bound:.0f}")
            for i, bound in enumerate(bounds)
        ] + [m_patches.Patch(color=li[-1], label=f"≥{bounds[-1]:.0f}")]
        plt.legend(handles=patches)
        return [li[i] for i in np.digitize(weights, bounds, right=True)]

        # rng, step = max_ - min_, (max_ - min_) / len(li)
        # # 49  -> 0, 50  -> 1, 80  -> 2, 110 -> 3,
        # # 140 -> 4, 170 -> 5, 199 -> 5, 200 -> 6
        # patches = [
        #     mpatches.Patch(color=li[i], label=f"<{min_ + step *i:.0f}") for i in range(len(li)-1)
        # ] + [mpatches.Patch(color=li[-1], label=f"≥{min_ + step * (len(li)-2):.0f}")]
        # plt.legend(handles=patches)
        #
        # return [li[int(min(max((w-min_+step) / rng * len(li), 0), len(li)-1))] for w in weights]

    """
    the distance in meters
    https://clouds.eos.ubc.ca/~phil/courses/atsc301/html/cartopy_mapping_pyproj.html
    """
    @staticmethod
    def distance(lat1: float, long1: float,  lat2: float, long2: float):
        _, _, dist = Karte.g.inv(long1, lat1, long2, lat2)
        return dist
        # return self.geo.geometry_length(LineString(longlat_list))

    @staticmethod
    def save(file_path):
        plt.savefig(file_path)
