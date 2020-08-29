import math
import re

import numpy as np

from converters.convert_lib import PointCollection


class ObjMaterial:
    def __init__(self, name):
        self.name = name
        self.ambient_map = None
        self.diffuse_map = None
        self.specular_map = None
        self.specular_highlight_map = None
        self.alpha_map = None
        self.displacement_map = None
        self.ambient_color = (0.5, 0.5, 0.5)
        self.diffuse_color = (0.5, 0.5, 0.5)
        self.specular_color = (0.33, 0.33, 0.33)
        self.specular_highlight = 0
        self.dissolve = 1
        self.optical_density = 1.5
        self.illumination = 2

    def get_maps(self):
        maps = set()
        maps.add(self.ambient_map)
        maps.add(self.diffuse_map)
        maps.add(self.specular_map)
        maps.add(self.specular_highlight_map)
        maps.add(self.alpha_map)
        maps.add(self.displacement_map)
        if None in maps:
            maps.remove(None)
        return maps


class ObjGeometry():
    def __init__(self, name):
        self.name = name
        self.triangles = []
        self.material = None
        self.smooth = False

    @staticmethod
    def normalize_indices_group(indices, data):
        minimum = math.inf
        maximum = -math.inf
        for x in indices:
            for ele in x:
                if ele < minimum:
                    minimum = ele
                if ele > maximum:
                    maximum = ele
        ret = np.array(data[minimum:maximum + 1], np.float)
        return ret, indices - minimum

    def normalize(self, vertices, normals, tex_coords):
        triangles = np.array(self.triangles)
        triangles = triangles - 1
        self.triangles = triangles
        self.vertices = PointCollection(*self.normalize_indices_group(triangles[:, :, 0], vertices))
        self.normals = PointCollection(*self.normalize_indices_group(triangles[:, :, 2], normals))
        self.texcoords = PointCollection(*self.normalize_indices_group(triangles[:, :, 1], tex_coords))


class Obj():
    class ObjParseException(BaseException):
        pass

    def __init__(self, filename):
        self.geometries = []
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.materials = {}
        self.images = set()
        self.mtllib = None
        self.filename = filename
        self.parse_file(filename)
        for geo in self.geometries:
            geo.normalize(self.vertices, self.normals, self.texcoords)

    def parse_words(self, words, geometry):
        start = words.pop(0)
        if start == 'v':
            self.vertices.append([float(x) for x in words])
        elif start == 'vt':
            self.texcoords.append([float(x) for x in words[:2]])
        elif start == 'vn':
            self.normals.append([float(x) for x in words])
        elif start == 'f':
            tri = []
            for x in words:
                t = x.split('/')
                tri.append([int(y) for y in t])
            geometry.triangles.append(tri)
        elif start == 'o' or start == 'g':
            return words[0]
        elif start == 'usemtl':
            geometry.material = words[0]
        elif start == 's':
            geometry.smooth = True
        elif start == 'mtllib':
            self.mtllib = words[0]
        else:
            raise self.ObjParseException('Unknown statement {} {}'.format(start, words.join(' ')))

    def parse_mtl_words(self, words, material):
        first = words.pop(0)
        if 'map' in first:
            map = words[-1]
            if first == 'map_Ka':
                material.ambient_map = map
            elif first == 'map_Kd':
                material.diffuse_map = map
            elif first == 'map_Ks':
                material.specular_map = map
            elif first == 'map_Ns':
                material.specular_highlight_map = map
            elif first in ('map_d', 'map_bump'):
                material.alpha_map = map
            self.images.add(map)
        elif first == 'newmtl':
            return words[0]
        elif first == 'Ka':
            material.ambient_color = [float(x) for x in words]
        elif first == 'Kd':
            material.diffuse_color = [float(x) for x in words]
        elif first == 'Ks':
            material.specular_color = [float(x) for x in words]
        elif first == 'Ns':
            material.specular_highlight = float(words[0])
        elif first == 'd':
            material.dissolve = float(words[0])
        elif first == 'Tr':
            material.dissolve = 1 - float(words[0])
        elif first == 'Ni':
            material.optical_density = float(words[0])
        elif first == 'illum':
            material.illumination = int(words[0])
        elif first == 'disp':
            material.displacement_map = words[-1]
            self.images.add(words[-1])

    def parse_mat_lib(self, mat_lib_path):
        material = None
        with open(mat_lib_path) as f:
            data = f.readlines()
            for line in data:
                if len(line) < 2 or line[0] == '#':
                    continue
                words = re.split("\s+", line.rstrip('\n').strip())
                new_mat = self.parse_mtl_words(words, material)
                if new_mat:
                    material = ObjMaterial(new_mat)
                    self.materials[new_mat] = material

    def parse_file(self, filename):
        geometry = None
        with open(filename) as f:
            data = f.readlines()
            for line in data:
                if len(line) < 2 or line[0] == '#':
                    continue
                words = re.split('\s+', line.rstrip('\n').strip())
                new_geo = self.parse_words(words, geometry)
                if new_geo:
                    if not geometry or geometry.name != new_geo:
                        geometry = ObjGeometry(new_geo)
                        self.geometries.append(geometry)
        if self.mtllib:
            self.parse_mat_lib(self.mtllib)
