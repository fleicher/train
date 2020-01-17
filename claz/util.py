import os
import pickle
from typing import Tuple, List

import numpy as np
import unidecode

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature
# import cartopy.geodesic
# from shapely.geometry import LineString
from pyproj import Geod

LAT_RANGE = (35.0, 65.0)  # y-axis
LONG_RANGE = (-11.0, 39.0)  # x-axis


def get_eu_map(figsize=(10, 6)):

    projection = ccrs.AlbersEqualArea(np.mean(LONG_RANGE), np.mean(LAT_RANGE))
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
    def __init__(self, figsize=(10, 6)):
        self.projection = ccrs.AlbersEqualArea(np.mean(LONG_RANGE), np.mean(LAT_RANGE))
        # self.geo = cartopy.geodesic.Geodesic()
        self.g = Geod(ellps='WGS84')
        plt.figure(figsize=figsize)
        self.ax = plt.axes(projection=self.projection)
        self.ax.set_extent(LONG_RANGE + LAT_RANGE)

        self.ax.add_feature(cartopy.feature.OCEAN)
        self.ax.add_feature(cartopy.feature.LAND, edgecolor='black')
        self.ax.add_feature(cartopy.feature.LAKES, edgecolor='black')

    def point(self, long, lat, text=None, color="black"):
        x, y = self.projection.transform_point(long, lat, ccrs.Geodetic())
        plt.plot(x, y, c=color)
        if text is not None:
            plt.text(x, y, s=text, c=color)

        """https://clouds.eos.ubc.ca/~phil/courses/atsc301/html/cartopy_mapping_pyproj.html"""
    def distance(self, long1, lat1, long2, lat2):
        _, _, dist = self.g.inv(long1, lat1, long2, lat2)
        return dist
        # return self.geo.geometry_length(LineString(longlat_list))

    @staticmethod
    def save(filepath):
        plt.savefig(filepath)
