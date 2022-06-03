import os
import sys

import numpy as np

from abmatt.autofix import AutoFix
from abmatt.converters.arg_parse import cmdline_convert
from abmatt.converters.convert_lib import Converter
from abmatt.converters.geometry import Geometry
from abmatt.converters.material import Material
from abmatt.converters.obj import Obj, ObjGeometry, ObjMaterial
from brres import Brres
from converters.colors import ColorCollection


class ObjConverter(Converter):

    def __collect_geometries(self, obj_geometries, bone):
        material_geometry_map = {}
        # first collect geometries
        for geometry in obj_geometries:
            if self._should_include_geometry(geometry):
                normals = None if self.NO_NORMALS & self.flags else geometry.normals
                texcoords = [geometry.texcoords] if geometry.has_texcoords else None
                geo = Geometry(geometry.name, geometry.material_name, geometry.vertices, texcoords, normals,
                               triangles=geometry.triangles, linked_bone=bone)
                # geo.encode(self.mdl0)
                mat = geometry.material_name
                if mat in material_geometry_map:
                    material_geometry_map[mat].combine(geo)
                else:
                    material_geometry_map[mat] = geo
                    self.geometries.append(geo)
        return material_geometry_map

    def load_model(self, model_name=None):
        mdl = self._start_loading(model_name)
        bone = mdl.add_bone(mdl.name)
        self.obj = obj = Obj(self.mdl_file)
        self.material_geometry_map = material_geometry_map = self.__collect_geometries(obj.geometries, bone)
        self._before_encoding()
        for material in material_geometry_map:
            super()._encode_geometry(material_geometry_map[material])
        self.import_textures_map = self.__convert_set_to_map(obj.images)
        return self._end_loading()

    def encode_materials(self):
        for material in self.material_geometry_map:
            try:
                self.__encode_material(self.obj.materials[material])
            except KeyError:
                self._encode_material(Material(material))

    def save_model(self, mdl0=None):
        base_name, mdl0 = self._start_saving(mdl0)
        polygons = self.polygons
        obj = Obj(self.mdl_file, False)
        obj_materials = obj.materials
        for mat in self.materials:
            obj_mat = self.__decode_material(mat)
            obj_materials[obj_mat.name] = obj_mat
        obj_geometries = obj.geometries
        has_colors = False
        for x in polygons:
            geometry = super()._decode_geometry(x)
            if geometry:
                material = geometry.material_name
                obj_geometries.append(self.__decode_geometry(geometry, material))
                if x.get_color_group():
                    has_colors = True
        if has_colors:
            AutoFix.warn('Loss of color data exporting obj')
        self._end_saving(obj)

    @staticmethod
    def __convert_map_to_layer(material, map):
        base_name = os.path.splitext(os.path.basename(map))[0]
        if not material.getLayerByName(base_name):
            return material.add_layer(base_name)

    def __convert_set_to_map(self, obj_images):
        path_map = {}
        for x in obj_images:
            path_map[os.path.splitext(os.path.basename(x))[0]] = x
        return path_map

    def __encode_material(self, obj_mat):
        return self._encode_material(Material(obj_mat.name, obj_mat.diffuse_map, obj_mat.ambient_map,
                                              obj_mat.specular_map, obj_mat.get_transparency()))

    @staticmethod
    def __decode_geometry(geometry, material_name):
        geo = ObjGeometry(geometry.name)
        geo.vertices = geometry.apply_linked_bone_bindings()
        geo.material_name = material_name
        geo.vertices = geometry.vertices
        geo.normals = geometry.normals
        geo.has_normals = bool(geo.normals)
        texcoords = geometry.texcoords
        if len(texcoords) > 1:
            AutoFix.warn('Loss of UV data for {}.'.format(geo.name))
        stack = [geo.vertices.face_indices]
        if len(texcoords):
            geo.texcoords = texcoords[0]
            stack.append(geo.texcoords.face_indices)
            geo.has_texcoords = True
        else:
            geo.texcoords = None
            geo.has_texcoords = False
        if geo.normals:
            stack.append(geo.normals.face_indices)
        geo.triangles = np.stack(stack, -1)
        return geo

    def __decode_material(self, material):
        mat = ObjMaterial(material.name)
        if material.xlu:
            mat.dissolve = 0.5
        first = True
        for layer in material.layers:
            name = layer.name
            if name not in self.tex0_map:
                tex = self.texture_library.get(name)
                if tex:
                    self.tex0_map[name] = tex
                else:
                    AutoFix.warn('No texture found matching {}'.format(name))
            if first:
                path = os.path.join(self.image_dir, name + '.png')
                mat.diffuse_map = path
                mat.ambient_map = path
            first = False
        return mat


def __load_vert_color(vert_color, geo, vertices):
    for vert in geo.vertices.points[geo.vertices.face_indices].reshape(-1, 3):
        t_vert = tuple(vert)
        if t_vert not in vertices:
            vertices[t_vert] = [vert_color]
        else:
            vertices[t_vert].append(vert_color)


def __apply_colors_to_geo(colors, geo, default_color):
    decoded = geo.get_decoded()
    points = np.around(decoded.vertices.points, 2)
    new_colors = []
    for point in points:
        color = colors.get(tuple(point)) #  or default_color
        new_colors.append(color)
    decoded.colors = ColorCollection(np.array(new_colors), decoded.vertices.face_indices, normalize=True)


def obj_mats_to_vertex_colors(polygons, obj, default_color=None, overwrite=False):
    if not overwrite:
        polygons = [x for x in polygons if not x.get_decoded().colors]
    if not polygons:
        return
    if not default_color:
        default_color = (0.5, 0.5, 0.5, 1)
    if type(obj) is not Obj:
        obj = Obj(obj)
    # Gather up color corresponding to each material
    mat_to_vert_color = {}
    for material in obj.materials.values():
        vertex_color = [x for x in material.diffuse_color]
        vertex_color.append(material.dissolve)
        mat_to_vert_color[material.name] = vertex_color

    vertices = {}
    for geo in obj.geometries:
        __load_vert_color(
            mat_to_vert_color.get(geo.material_name),
            geo,
            vertices
        )
    # now interpolate colors
    interpolated = {}
    for vert, colors in vertices.items():
        colors = np.around(colors, 2)
        interpolated[vert] = [sum(colors[:, i]) / len(colors) for i in range(4)]

    for x in polygons:
        __apply_colors_to_geo(interpolated, x, default_color)
        x.get_decoded().recode(x)


def main():
    cmdline_convert(sys.argv[1:], '.obj', ObjConverter)


if __name__ == '__main__':
    main()
