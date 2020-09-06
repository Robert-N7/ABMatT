import os
import sys
import time
from xml.etree import ElementTree

import numpy as np
import collada
from collada.scene import ControllerNode, GeometryNode, Node, ExtraNode
from collada import source

from brres import Brres
from brres.mdl0 import Mdl0
from brres.mdl0.material import Material
from brres.tex0 import EncodeError, ImgConverter
from converters.convert_lib import add_geometry, PointCollection, ColorCollection, Converter, decode_polygon
from converters.arg_parse import arg_parse, cmdline_convert


class DaeConverter(Converter):
    @staticmethod
    def convert_map_to_layer(map, material, image_path_map):
        if not map or isinstance(map, tuple):
            return
        sampler = map.sampler
        base_name = image_path_map[sampler.surface.image.path]
        # create the layer
        if not material.getLayerByName(base_name):
            l = material.addLayer(base_name)
            if sampler.minfilter:
                pass  # todo update layer minfilter
            coord = 'texcoord' + map.texcoord[-1]
            l.setCoordinatesStr(coord)

    @staticmethod
    def encode_material(dae_material, mdl, image_path_map):
        m = Material.get_unique_material(dae_material.name, mdl)
        mdl.add_material(m)
        effect = dae_material.effect
        if effect.double_sided:
            m.cullmode = 0
        if effect.transparency > 0:
            m.enable_blend()
        # maps
        DaeConverter.convert_map_to_layer(effect.diffuse, m, image_path_map)
        DaeConverter.convert_map_to_layer(effect.ambient, m, image_path_map)
        DaeConverter.convert_map_to_layer(effect.specular, m, image_path_map)
        DaeConverter.convert_map_to_layer(effect.reflective, m, image_path_map)
        DaeConverter.convert_map_to_layer(effect.bumpmap, m, image_path_map)
        DaeConverter.convert_map_to_layer(effect.transparent, m, image_path_map)
        return m

    def encode_geometry(self, geometry, bone):
        mdl = self.mdl
        name = geometry.id
        if not name:
            name = geometry.name
        # if not np.allclose(geometry.matrix, self.IDENTITY_MATRIX):
        #     bone = mdl.add_bone(name, bone)
        #     set_bone_matrix(bone, geometry.matrix)

        for triset in geometry.primitives:
            # material
            name = triset.material
            mat = self.materials.get(name)
            if not mat:
                material = Material.get_unique_material(name, mdl)
                mdl.add_material(material)
                if name in self.image_path_map:
                    material.addLayer(name)
            else:
                material = self.encode_material(mat, mdl, self.image_path_map)
            # triset.index[:,[0, 1]] = triset.index[:,[1, 0]]
            vertex_group = PointCollection(triset.vertex, triset.vertex_index)
            if self.flags & self.NoNormals or triset.normal is None or material.is_cull_none() or self.is_map:
                normal_group = None
            else:
                normal_group = PointCollection(triset.normal, triset.normal_index)
            tex_coords = []
            for i in range(len(triset.texcoordset)):
                tex_set = triset.texcoordset[i]
                tex_coords.append(PointCollection(tex_set, triset.texcoord_indexset[i]))
            if self.flags & self.NoColors:
                colors = None
            else:
                colors = triset.sources.get('COLOR')
                if colors:
                    color_source = colors[0]
                    face_indices = triset.index[:, :, color_source[0]]
                    colors = ColorCollection(color_source[4].data[:np.max(face_indices) + 1], face_indices,
                                             normalize=True)
                    colors.normalize()
            poly = add_geometry(mdl, name, vertex_group, normal_group,
                                colors, tex_coords)
            mdl.add_definition(material, poly, bone)
            if colors:
                material.enable_vertex_color()
            break

    @staticmethod
    def get_geometry_by_id(geometries, id):
        geo = geometries[id]
        for x in geometries:
            if x.id == id:
                return x

    @staticmethod
    def node_has_children(children):
        for x in children:
            if type(x) == Node:
                return True
        return False

    def parse_nodes(self, nodes, parent_bone, mdl):
        for node in nodes:
            t = type(node)
            if t == ExtraNode:
                continue
            if t == Node:
                has_identity_matrix = self.is_identity_matrix(node.matrix)
                has_child_bones = self.node_has_children(node.children)
                has_children = len(node.children) > 0
            else:
                has_identity_matrix = True
                has_children = has_child_bones = False
            if not has_identity_matrix or not parent_bone or has_child_bones:
                bone = mdl.add_bone(node.id, parent_bone)
                if not has_identity_matrix:
                    self.set_bone_matrix(bone, node.matrix)
                if not parent_bone:
                    parent_bone = bone
            else:
                bone = parent_bone

            geo = None
            if t == ControllerNode:
                geo = node.controller.geometry
            elif t == GeometryNode:
                geo = node.geometry
            else:
                geo = self.geometries.get(node.id)
            if geo:
                if not bone:
                    bone = mdl.add_bone()
                self.encode_geometry(geo, bone)
            if has_children:
                self.parse_nodes(node.children, bone, mdl)

    def load_model(self, model_name=None):
        brres = self.brres
        model_file = self.mdl_file
        cwd = os.getcwd()
        dir, name = os.path.split(brres.name)
        base_name = os.path.splitext(name)[0]
        self.is_map = True if 'map' in name else False
        if dir:
            os.chdir(dir)  # change to the collada dir to help find relative paths
        print('Converting {}... '.format(self.mdl_file))
        start = time.time()
        dae = collada.Collada(model_file, ignore=[collada.DaeIncompleteError, collada.DaeUnsupportedError, collada.DaeBrokenRefError])
        if not model_name:
            model_name = base_name.replace('_model', '')
        self.mdl = mdl = Mdl0(model_name, brres)
        # images
        self.image_path_map = image_path_map = {}
        for image in dae.images:
            image_path_map[image.path] = self.try_import_texture(brres, image.path)
        if not brres.textures and len(dae.images):
            print('ERROR: No textures found!')
        self.materials = dae.materials
        self.geometries = dae.geometries
        # geometry
        scene = dae.scene
        self.parse_nodes(scene.nodes, None, mdl)
        mdl.rebuild_header()
        # add model to brres
        brres.add_mdl0(mdl)
        if self.is_map:
            mdl.add_map_bones()
        os.chdir(cwd)
        print('\t... Finished in {} secs'.format(round(time.time() - start, 2)))
        return mdl

    @staticmethod
    def convert_colors(color_group):
        return color_group

    @staticmethod
    def construct_indices(triset_group, stride=3):
        geo_group = []
        ln = 0
        indices = []
        b = stride
        c = b + stride
        maximum = triset_group[0][:b]
        minimum = [x for x in maximum]
        for x in triset_group:
            points = [x[:b], x[b:c], x[c:]]
            for point in points:
                found = False
                for i in range(ln):
                    if point == geo_group[i]:
                        indices.append(i)
                        found = True
                        break
                if not found:
                    geo_group.append(point)
                    for i in range(3):
                        if point[i] < minimum[i]:
                            minimum[i] = point[i]
                        elif point[i] > maximum[i]:
                            maximum[i] = point[i]
                    indices.append(ln)
                    ln += 1
        return PointCollection(geo_group, indices, minimum, maximum)

    def decode_material(self, brres_mat, mesh):
        name = brres_mat.name
        ambient = diffuse = specular = (0.6, 0.6, 0.6, 1.0)
        bumpmap = None
        map_index = 0
        effect_params = []
        for layer in brres_mat.layers:
            layer_name = layer.name
            found_tex = True
            if layer_name not in self.tex0_map:
                tex = self.texture_library.get(layer_name)
                path = os.path.join(self.image_dir, layer_name + '.png') if tex else '\n\t'
                self.tex0_map[layer_name] = (tex, path)
            else:
                path = self.tex0_map[layer_name][1]
            cimage = collada.material.CImage(layer_name, path, mesh)
            mesh.images.append(cimage)
            surface = collada.material.Surface(layer_name + '-surface', cimage, 'A8R8G8B8')
            sampler2d = collada.material.Sampler2D(layer_name, surface,
                                                   layer.getMinfilter().upper(), layer.getMagfilter().upper())
            sampler2d.xmlnode.attrib['path'] = path
            # effect_params.append(surface)
            effect_params.append(sampler2d)
            texcoord = layer.getCoordinates()[-1]
            channel = texcoord if texcoord.isdigit() else '0'
            map = collada.material.Map(sampler2d, 'CHANNEL' + channel)
            if map_index == 0:
                diffuse = map
            elif map_index == 1:
                ambient = map
            elif map_index == 2:
                specular = map
            elif map_index == 3:
                bumpmap = map
            map_index += 1
        double_sided = True if not brres_mat.cullmode else False
        transparency = 0.5 if brres_mat.xlu else float(0)
        effect = collada.material.Effect(name + '-effect', effect_params, 'phong',
                                 double_sided=double_sided, transparency=transparency,
                                 diffuse=diffuse, ambient=ambient, specular=specular, bumpmap=bumpmap)
        mesh.effects.append(effect)
        mat = collada.material.Material(name + '-mat', name, effect)
        return mat

    def decode_geometry(self, polygon, mesh):
        decoded_geom = decode_polygon(polygon)
        name = polygon.name
        mat = decoded_geom['material']
        collada_material = self.decode_material(mat, mesh)
        mesh.materials.append(collada_material)
        verts = decoded_geom['vertices']
        normals = decoded_geom['normals']
        colors = decoded_geom['colors']
        texcoords = decoded_geom['texcoords']
        srcs = []
        src_index = 0
        input_list = source.InputList()
        vert_name = name + '_vertices'
        vert_src = source.FloatSource(vert_name, verts.points, ('X', 'Y', 'Z'))
        srcs.append(vert_src)
        input_list.addInput(src_index, 'VERTEX', '#' + vert_name)
        src_index += 1
        if normals:
            normal_name = name + '_normals'
            normal_src = collada.source.FloatSource(normal_name, normals.points, ('X', 'Y', 'Z'))
            srcs.append(normal_src)
            input_list.addInput(src_index, 'NORMAL', '#' + normal_name)
            src_index += 1
        if colors:
            color_name = name + '_colors'
            color_src = collada.source.FloatSource(color_name, colors.denormalize(), ('R', 'G', 'B', 'A'))
            srcs.append(color_src)
            input_list.addInput(src_index, 'COLOR', '#' + color_name, '0')
            src_index += 1
        for i in range(len(texcoords)):
            x = texcoords[i]
            tex_name = name + '_UV' + str(i)
            tex_src = collada.source.FloatSource(tex_name, x.points, ('S', 'T'))
            srcs.append(tex_src)
            input_list.addInput(src_index, 'TEXCOORD', '#' + tex_name, str(i))
            src_index += 1
        poly_name = polygon.name + '-lib'
        geo = collada.geometry.Geometry(mesh, poly_name, poly_name, srcs)
        triset = geo.createTriangleSet(decoded_geom['triangles'], input_list, mat.name)
        geo.primitives.append(triset)
        mesh.geometries.append(geo)
        matnode = collada.scene.MaterialNode(mat.name, collada_material, inputs=[])
        geomnode = collada.scene.GeometryNode(geo, [matnode])
        # set up controller
        # ctrl_name = name + '-Controller'
        # joint_src = ctrl_name + '-Joints'
        # vertex_inf_counts = np.full(vert_len, 1, int)
        # x = np.zeros(vert_len, dtype=int)
        # y = np.arange(1, vert_len + 1, dtype=int)
        # vertex_weight_index = np.stack([x, y], 1).flatten()
        # # weird workarounds to prevent missed imports in pycollada
        # xmlnode = ElementTree.Element(collada.tag('controller'))
        # xmlnode.set('id', ctrl_name)
        # control = collada.controller.Skin(ctrl_name, self.identity_matrix, joint_src, ctrl_name + '-Matrices', ctrl_name + '-Weights',
        #                           joint_src, vertex_inf_counts, vertex_weight_index, [0, 1], geo, xmlnode)
        # xmlnode = ElementTree.Element(collada.tag('instance_controller'))
        # bindnode = ElementTree.Element(collada.tag('bind_material'))
        # technode = ElementTree.Element(collada.tag('technique_common'))
        # bindnode.append(technode)
        # technode.append(collada_material.xmlnode)
        # control_node = collada.scene.ControllerNode(control, [collada_material], xmlnode)
        # control_node.xmlnode.append(bindnode)
        # mesh.controllers.append(control)
        node = collada.scene.Node(name, children=[geomnode])
        return node

    def decode_bone(self, bone):
        children = bone.get_children()
        decoded_children = []
        if children:
            for child in children:
                decoded_children.append(self.decode_bone(child))
        matrix = np.array(bone.get_transform_matrix(), np.float)
        scene_matrix = collada.scene.MatrixTransform(matrix.flatten())
        node = Node(bone.name, transforms=[scene_matrix], children=decoded_children)
        self.bone_transform_matrix[bone.index] = matrix if not self.is_identity_matrix(matrix) else None
        return node

    def save_model(self, mdl0=None):
        print('INFO: Exporting to {}...'.format(self.mdl_file))
        start = time.time()
        if not mdl0:
            mdl0 = self.brres.models[0]
        cwd = os.getcwd()
        dir, name = os.path.split(self.mdl_file)
        if dir:
            os.chdir(dir)
        base_name, ext = os.path.splitext(name)
        self.image_dir = base_name + '_maps'
        self.texture_library = self.brres.get_texture_map()
        self.tex0_map = {}
        mesh = collada.Collada()
        polygons = mdl0.objects
        self.bone_transform_matrix = {}
        # todo, fix up bones
        nodes = []
        nodes.append(self.decode_bone(mdl0.bones[0]))
        self.identity_matrix = np.eye(4).flatten()
        for polygon in polygons:
            nodes.append(self.decode_geometry(polygon, mesh))
        my_scene = collada.scene.Scene(mdl0.name, nodes)
        mesh.scenes.append(my_scene)
        mesh.scene = my_scene
        # images
        if len(self.tex0_map):
            if not os.path.exists(self.image_dir):
                os.mkdir(self.image_dir)
            os.chdir(self.image_dir)
            converter = ImgConverter()
            for image_name in self.tex0_map:
                tex, path = self.tex0_map[image_name]
                if not tex:
                    print('WARN: Missing texture {}'.format(image_name))
                    continue
                converter.decode(tex, image_name + '.png')
        os.chdir(cwd)
        mesh.write(self.mdl_file)
        # little annoying fix to put in xml tag
        data = None
        with open(self.mdl_file, 'r') as f:
            data = f.read()
        if data:
            data = '<?xml version="1.0" encoding="utf-8"?>\n' + data
            with open(self.mdl_file, 'w') as f:
                f.write(data)
        print('\t...finished in {} seconds.'.format(round(time.time() - start, 2)))


def main():
    cmdline_convert(sys.argv[1:], '.dae', DaeConverter)


if __name__ == '__main__':
    main()
