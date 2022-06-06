import os
import re

import numpy as np

from abmatt import __version__
from abmatt.autofix import AutoFix
from abmatt.converters.convert_lib import float_to_str
from abmatt.converters.points import PointCollection


class ObjMaterial:
    def __init__(self, name, diffuse_color=(0.5, 0.5, 0.5), diffuse_map=None, dissolve=1):
        self.name = name
        self.ambient_map = None
        self.diffuse_map = diffuse_map
        self.specular_map = None
        self.specular_highlight_map = None
        self.alpha_map = None
        self.displacement_map = None
        self.ambient_color = (0.5, 0.5, 0.5)
        self.diffuse_color = diffuse_color
        self.specular_color = (0.33, 0.33, 0.33)
        self.specular_highlight = 0
        self.dissolve = dissolve
        self.optical_density = 1.5
        self.illumination = 2

    def get_transparency(self):
        return 1 - self.dissolve

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

    def get_save_str(self):
        s = 'newmtl ' + self.name + '\n\tNs ' + str(self.specular_highlight) + \
            '\n\tNi ' + str(self.optical_density) + '\n\td ' + str(self.dissolve) + \
            '\n\tTr ' + str(1 - self.dissolve) + '\n\tillum ' + str(self.illumination) +\
            '\n\tKa ' + ' '.join([float_to_str(x) for x in self.ambient_color]) + \
            '\n\tKd ' + ' '.join([float_to_str(x) for x in self.diffuse_color]) + \
            '\n\tKs ' + ' '.join([float_to_str(x) for x in self.specular_color])
        if self.ambient_map:
            s += '\n\tmap_Ka ' + self.ambient_map
        if self.diffuse_map:
            s += '\n\tmap_Kd ' + self.diffuse_map
        if self.specular_map:
            s += '\n\tmap_Ks ' + self.specular_map
        if self.specular_highlight_map:
            s += '\n\tmap_Ns ' + self.specular_highlight_map
        if self.alpha_map:
            s += '\n\tmap_d ' + self.alpha_map
        return s + '\n'


class ObjGeometry():
    def __init__(self, name):
        self.name = name
        self.triangles = []
        self.texcoords = self.normals = self.vertices = None
        self.material_name = None
        self.has_normals = self.has_texcoords = False
        self.smooth = False

    def add_tri(self, tri):
        self.triangles.append(tri)

    @staticmethod
    def normalize_indices_group(indices, data):
        minimum = indices.min()
        maximum = indices.max()
        # for x in indices:
        #     for ele in x:
        #         if ele < minimum:
        #             minimum = ele
        #         if ele > maximum:
        #             maximum = ele
        ret = np.array(data[minimum:maximum + 1], np.float)
        return PointCollection(ret, indices - minimum)

    def normalize(self, vertices, normals, tex_coords):
        width = 1 + self.has_normals + self.has_texcoords
        try:
            triangles = np.array(self.triangles).reshape((-1, 3, width))
        except ValueError as e:
            AutoFix.warn('Please triangulate your model before importing it!'.format(self.name))
            raise ValueError('Normalize triangles failed')
        triangles = triangles - 1
        self.vertices = self.normalize_indices_group(triangles[:, :, 0], vertices)
        tris = [self.vertices.face_indices]
        if self.has_normals:
            self.normals = self.normalize_indices_group(triangles[:, :, -1], normals)
            tris.append(self.normals.face_indices)
        if self.has_texcoords:
            self.texcoords = self.normalize_indices_group(triangles[:, :, 1], tex_coords)
            tris.append(self.texcoords.face_indices)
        self.triangles = np.stack(tris, axis=-1)


class Obj():
    class ObjParseException(BaseException):
        pass

    def __init__(self, filename, read_file=True):
        self.geometries = []
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.materials = {}
        self.images = set()
        self.filename = filename
        if read_file:
            self.mtllib = None
            self.__parse_file(filename)
            to_remove = []
            for geo in self.geometries:
                try:
                    geo.normalize(self.vertices, self.normals, self.texcoords)
                except ValueError:
                    to_remove.append(geo)
                    AutoFix.warn('No geometry found for {}'.format(geo.name))
            if to_remove:
                self.geometries = [x for x in self.geometries if x not in to_remove]
        else:
            dir, name = os.path.split(filename)
            base_name = os.path.splitext(name)[0]
            self.mtllib = base_name + '.mtl'

    def write(self, filename):
        self.filename = filename
        self.save()

    def save(self):
        folder, name = os.path.split(self.filename)
        self.__save_mtllib(folder)
        self.save_obj()

    def get_material(self, name):
        return self.materials.get(name)

    def __save_mtllib(self, folder):
        s = '# Wavefront MTL exported with ABMATT ' + __version__
        materials = self.materials
        for x in materials:
            s += '\n' + materials[x].get_save_str()
        with open(os.path.join(folder, self.mtllib), 'w') as f:
            f.write(s)

    def save_obj(self):
        s = '# Wavefront OBJ exported with ABMATT ' + __version__ + \
            '\n\nmtllib ' + self.mtllib + '\n\n'
        vertex_index = 1
        normal_index = 1
        normal_offset = -1
        texcoord_index = 1
        smooth = False
        for geometry in self.geometries:
            s += '#\n# object ' + geometry.name + '\n#\n\n'
            vertex_count = len(geometry.vertices)
            for vert in geometry.vertices:
                s += 'v ' + ' '.join(float_to_str(x) for x in vert) + '\n'
            s += '# {} vertices\n\n'.format(vertex_count)
            if geometry.normals:
                normal_count = len(geometry.normals)
                for normal in geometry.normals:
                    s += 'vn ' + ' '.join(float_to_str(x) for x in normal) + '\n'
                s += '# {} normals\n\n'.format(normal_count)
            else:
                normal_count = 0
            if geometry.texcoords:
                texcoord_count = len(geometry.texcoords)
                for texcoord in geometry.texcoords:
                    s += 'vt ' + ' '.join(float_to_str(x) for x in texcoord) + '\n'
                s += '# {} texture coordinates\n\n'.format(texcoord_count)
                texcoord_offset = 1
            else:
                texcoord_offset = -1
            # now adjust the tri indices
            tris = np.copy(geometry.triangles)
            tris[:, :, 0] = tris[:, :, 0] + vertex_index
            if texcoord_offset > 0:
                tris[:, :, texcoord_offset] = tris[:, :, texcoord_offset] + texcoord_index
            if normal_count:
                tris[:, :, normal_offset] = tris[:, :, normal_offset] + normal_index
            # start the group of indices
            s += 'o {}\ng {}\n'.format(geometry.name, geometry.name)
            s += 'usemtl {}\n'.format(geometry.material_name)
            if geometry.smooth != smooth:
                s += 's off\n' if not geometry.smooth else 's\n'
                smooth = geometry.smooth
            joiner = '/' if geometry.texcoords else '//'
            for tri in tris:
                s += 'f ' + ' '.join([joiner.join([str(x) for x in fp]) for fp in tri]) + '\n'
            s += '# {} triangles\n\n'.format(len(tris))
            # now increase the indices
            vertex_index += vertex_count
            normal_index += normal_count
            if geometry.texcoords:
                texcoord_index += texcoord_count
        with open(self.filename, 'w') as f:
            f.write(s)

    def __parse_words(self, words, geometry):
        start = words.pop(0)
        if start == 'v':
            self.vertices.append([float(x) for x in words])
        elif start == 'vt':
            self.texcoords.append([float(x) for x in words[:2]])
        elif start == 'vn':
            self.normals.append([float(x) for x in words])
        elif start == 'f':
            tri = []
            if self.start_new_geo:
                first_word = words[0]
                slash_one = first_word.find('/')
                if slash_one >= 0:
                    if first_word[slash_one + 1] != '/':
                        geometry.has_texcoords = True
                    slash_two = first_word.find('/', slash_one + 1)
                    if slash_two > 0:
                        geometry.has_normals = True
                self.start_new_geo = False
            for x in words:
                t = x.split('/')
                tri.append([int(y) for y in t])
            geometry.add_tri(tri)
        elif start == 'o' or start == 'g':
            return words[0]
        elif start == 'usemtl':
            geometry.material_name = words[0]
        elif start == 's':
            geometry.smooth = True
        elif start == 'mtllib':
            self.mtllib = words[0]
        else:
            raise self.ObjParseException('Unknown statement {} {}'.format(start, ' '.join(words)))

    def __parse_mtl_words(self, words, material):
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

    def __parse_mat_lib(self, mat_lib_path):
        material = None
        with open(mat_lib_path) as f:
            data = f.readlines()
            for line in data:
                if len(line) < 2 or line[0] == '#':
                    continue
                words = re.split(r"\s+", line.rstrip('\n').strip())
                new_mat = self.__parse_mtl_words(words, material)
                if new_mat:
                    material = ObjMaterial(new_mat)
                    self.materials[new_mat] = material

    def __parse_file(self, filename):
        geometry = None
        self.start_new_geo = False
        with open(filename) as f:
            data = f.readlines()
            for line in data:
                if len(line) < 2 or line[0] == '#':
                    continue
                words = re.split(r'\s+', line.rstrip('\n').strip())
                new_geo = self.__parse_words(words, geometry)
                if new_geo:
                    if not geometry or geometry.name != new_geo:
                        geometry = ObjGeometry(new_geo)
                        self.geometries.append(geometry)
                        self.start_new_geo = True
        if self.mtllib:
            if not os.path.exists(self.mtllib):
                self.mtllib = os.path.join(os.path.dirname(filename), self.mtllib)
            try:
                self.__parse_mat_lib(self.mtllib)
            except FileNotFoundError as e:
                AutoFix.error(str(e))

