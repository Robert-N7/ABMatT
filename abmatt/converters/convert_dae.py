import os
import sys
import time

import collada
import numpy as np
from collada import source
from collada.scene import ControllerNode, GeometryNode, Node, ExtraNode

from brres.mdl0 import Mdl0
from brres.tex0 import ImgConverter
from converters.arg_parse import cmdline_convert
from converters.convert_lib import add_geometry, PointCollection, ColorCollection, Converter, decode_polygon, \
    get_default_controller, Material
from converters.dae import Dae, ColladaNode


class DaeConverter2(Converter):

    def load_model(self, model_name=None):
        brres = self.brres
        model_file = self.mdl_file
        cwd = os.getcwd()
        self.bones = {}
        dir, name = os.path.split(brres.name)
        base_name = os.path.splitext(name)[0]
        self.is_map = True if 'map' in name else False
        if dir:
            os.chdir(dir)  # change to the collada dir to help find relative paths
        print('INFO: Converting {}... '.format(self.mdl_file))
        start = time.time()
        dae = Dae(model_file)
        if not model_name:
            model_name = base_name.replace('_model', '')
        self.mdl = mdl = Mdl0(model_name, brres)
        self.__parse_images(dae.get_images(), brres)
        self.__parse_materials(dae.get_materials())
        # geometry
        self.__parse_nodes(dae.get_scene())
        mdl.rebuild_header()
        brres.add_mdl0(mdl)
        if self.is_map:
            mdl.add_map_bones()
        os.chdir(cwd)
        print('\t... finished in {} secs'.format(round(time.time() - start, 2)))
        return mdl

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
        mesh = Dae(initial_scene_name=base_name)
        # materials
        for material in mdl0.materials:
            mesh.add_material(self.__decode_material(material))
        # polygons
        polygons = mdl0.objects
        mesh.add_node(self.__decode_bone(mdl0.bones[0]))
        for polygon in polygons:
            mesh.add_node(self.__decode_geometry(polygon))
        # images
        self.__create_image_library(mesh)
        os.chdir(cwd)
        mesh.write(self.mdl_file)
        print('\t...finished in {} seconds.'.format(round(time.time() - start, 2)))

    def __decode_bone(self, mdl0_bone, collada_parent=None):
        name = mdl0_bone.name
        node = ColladaNode(name, {'type': 'JOINT'})
        node.matrix = np.array(mdl0_bone.get_transform_matrix())
        if collada_parent:
            collada_parent.nodes.append(node)
        if mdl0_bone.child:
            self.__decode_bone(mdl0_bone.child, node)
        if mdl0_bone.next:
            self.__decode_bone(mdl0_bone.next, collada_parent)
        return node

    @staticmethod
    def __decode_geometry(polygon):
        name = polygon.name
        node = ColladaNode(name)
        node.geometry = decode_polygon(polygon)
        node.controller = get_default_controller(node.geometry, [polygon.get_bone().name])
        return node

    def __decode_material(self, material):
        diffuse_map = ambient_map = specular_map = None
        for i in range(len(material.layers)):
            layer = material.layers[i].name
            if i == 0:
                diffuse_map = layer
            elif i == 1:
                ambient_map = layer
            elif i == 2:
                specular_map = layer
            if layer not in self.tex0_map:
                tex0 = self.texture_library.get(layer)
                map_path = os.path.join(self.image_dir, layer + '.png')
                self.tex0_map[layer] = (tex0, map_path)
        return Material(material.name, diffuse_map, ambient_map, specular_map, material.xlu * 0.5)

    def __create_image_library(self, mesh):
        if len(self.tex0_map):
            if not os.path.exists(self.image_dir):
                os.mkdir(self.image_dir)
            os.chdir(self.image_dir)
            converter = ImgConverter()
            for image_name in self.tex0_map:
                tex, path = self.tex0_map[image_name]
                mesh.add_image(image_name, path)
                if not tex:
                    print('WARN: Missing texture {}'.format(image_name))
                    continue
                converter.decode(tex, image_name + '.png')

    def __parse_controller(self, controller):
        bones = controller.bones
        if controller.has_multiple_weights():
            raise self.ConvertError('ERROR: Multiple bone bindings not supported!')
        bone = self.bones[bones[0]]
        controller.geometry.encode(self.mdl, bone)

    def __add_bone(self, node, parent_bone=None):
        name = node.attributes['id']
        self.bones[name] = bone = self.mdl.add_bone(name, parent_bone)
        self.set_bone_matrix(bone, node.matrix)
        for n in node.nodes:
            self.__add_bone(n, bone)

    def __parse_nodes(self, nodes):
        for node in nodes:
            if node.controller:
                self.__parse_controller(node.controller)
            elif node.geometry:
                node.geometry.encode(self.mdl)
            elif node.attributes.get('type') == 'JOINT':
                self.__add_bone(node)
            self.__parse_nodes(node.nodes)

    def __parse_materials(self, materials):
        for material in materials:
            material.encode(self.mdl)

    def __parse_images(self, images, brres):
        # images
        self.image_path_map = image_path_map = {}
        for image in images:
            path = images[image]
            image_path_map[path] = self.try_import_texture(brres, path)
        if not brres.textures and len(images):
            print('ERROR: No textures found!')

def main():
    cmdline_convert(sys.argv[1:], '.dae', DaeConverter2)


if __name__ == '__main__':
    main()
