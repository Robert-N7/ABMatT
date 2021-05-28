from abmatt.lib.binfile import Folder, PackingError
from abmatt.lib.indexing import rebuild_indexes
from abmatt.lib.pack_interface import Packer
from abmatt.brres.lib.packing.pack_mdl0.pack_bone import PackBone
from abmatt.brres.lib.packing.pack_mdl0.pack_color import PackColor
from abmatt.brres.lib.packing.pack_mdl0.pack_material import PackMaterial
from abmatt.brres.lib.packing.pack_mdl0.pack_point import PackVertex, PackNormal, PackUV
from abmatt.brres.lib.packing.pack_mdl0.pack_polygon import PackPolygon
from abmatt.brres.lib.packing.pack_mdl0.pack_shader import PackShader
from abmatt.brres.lib.packing.pack_subfile import PackSubfile
from abmatt.brres.mdl0.definition import DrawList


class PackMdl0(PackSubfile):
    SECTION_NAMES = ("Definitions", "Bones", "Vertices", "Normals", "Colors",
                     "UVs", "FurVectors", "FurLayers",
                     "Materials", "Shaders", "Objects", "Textures", "Palettes")

    def pack(self, mdl0, binfile):
        """ Packs the model data """
        self.sections = self.pre_pack(mdl0)
        if self.sections[6] or self.sections[7]:
            raise PackingError(binfile, 'Packing Fur not supported')
        super(PackMdl0, self).pack(mdl0, binfile)
        binfile.start()  # header
        binfile.write('I', 0x40)
        binfile.write_outer_offset()
        # binfile.linked_offsets.extend([binfile.offset + 8, binfile.offset + 12])    #- debug
        binfile.write("7I", mdl0.scaling_rule, mdl0.texture_matrix_mode,
                      mdl0.facepoint_count, mdl0.face_count, 0, len(mdl0.bones), 0x01000000)
        binfile.mark()  # bone table offset
        if mdl0.version >= 10:
            binfile.write("6f", mdl0.minimum[0], mdl0.minimum[1], mdl0.minimum[2],
                          mdl0.maximum[0], mdl0.maximum[1], mdl0.maximum[2])
        binfile.create_ref()  # bone table
        self.pack_bonetable(mdl0.bone_table)
        binfile.end()  # end header
        # sections
        folders = self.packFolders(binfile)

        # texture links
        texture_link_map = self.packTextureLinks(binfile, folders[11])
        self.pack_definitions(binfile, folders[0])
        self.pack_section(binfile, 1, folders[1], PackBone)  # bones
        i = 8
        self.pack_materials(binfile, folders[i], texture_link_map)
        i += 1
        self.pack_shaders(binfile, folders[i])
        i += 1
        self.pack_section(binfile, 10, folders[i], PackPolygon)  # objects
        i = 2
        self.pack_section(binfile, i, folders[i], PackVertex)
        i += 1
        self.pack_section(binfile, i, folders[i], PackNormal)
        i += 1
        self.pack_section(binfile, i, folders[i], PackColor)
        i += 1
        self.pack_section(binfile, i, folders[i], PackUV)
        binfile.align_and_end()  # end file

    def pack_bonetable(self, table):
        self.binfile.write('I', len(table))
        self.binfile.write('{}i'.format(len(table)), *table)

    class TextureLink:
        def __init__(self, name, num_refs):
            self.name = name
            self.num_refs = num_refs

    class PackTextureLink(Packer):
        """ Links from textures to materials and layers """

        def __init__(self, name, binfile, num_references=1):
            """Only tracks number of references, which serve as placeholders to be filled in by the layers"""
            self.num_references = num_references
            self.name = name
            self.offset = 0
            super().__init__(num_references, binfile)

        def __str__(self):
            return self.name + ' ' + str(self.num_references)

        def pack(self, num_references, binfile):
            self.offset = binfile.start()
            binfile.write("I", num_references)
            for i in range(num_references):
                binfile.mark(2)  # marks 2 references
            binfile.end()

        def get_offset(self):
            return self.offset

    def packTextureLinks(self, binfile, folder):
        """Packs texture link section, returning map of names:offsets be filled in by mat/layer refs"""
        # binfile.section_offsets.append((binfile.offset, 'Textures'))       #- debug
        tex_map = {}
        links = self.sections[11]
        for x in links:
            folder.create_entry_ref_i()
            tex_map[x.name] = self.PackTextureLink(x.name, binfile, x.num_refs)
        return tex_map

    def pack_definitions(self, binfile, folder):
        # self.binfile.section_offsets.append((binfile.offset, folder.name))    #- debug
        for x in self.sections[0]:
            folder.create_entry_ref_i()
            x.pack(binfile)
        binfile.align(4)

    def pack_materials(self, binfile, folder, texture_link_map):
        """packs materials, requires texture link map to offsets that need to be filled"""
        # self.binfile.section_offsets.append((binfile.offset, folder.name))     #- debug
        mat_packers = self.mat_packers
        section = self.sections[8]
        for i in range(len(section)):
            mat = section[i]
            folder.create_entry_ref_i()
            mat_packers[mat.name] = PackMaterial(mat, binfile, i, texture_link_map)
        for x in texture_link_map:
            if binfile.references[texture_link_map[x].offset]:
                raise PackingError(binfile, 'Unused texture link {}!'.format(x))

    def pack_shaders(self, binfile, folder):
        # self.binfile.section_offsets.append((binfile.offset, folder.name))     #- debug
        shaders = self.shaders
        shader_mats = self.shader_mats
        mat_packers = self.mat_packers
        for i in range(len(shaders)):
            # create index group and material refs
            for mat in shader_mats[i]:
                name = mat.name
                folder.create_entry_ref(name)
                mat_packers[name].create_shader_ref(binfile)
            # pack the shader
            PackShader(shaders[i], binfile, i)

    def pack_section(self, binfile, section_index, folder, packer):
        """ Packs a model section (generic) """
        section = self.sections[section_index]
        if section:
            # binfile.section_offsets.append((binfile.offset, folder.name))  #- debug
            # now pack the data
            for i in range(len(section)):
                x = section[i]
                folder.create_entry_ref_i()  # create reference to current data location
                packer(x, binfile, i)

    def packFolders(self, binfile):
        """ Generates the root folders
            Does not hook up data pointers except the head group,
            returns rootFolders
        """
        root_folders = []  # for storing Index Groups
        sections = self.sections
        # Create folder for each section the MDL0 has
        i = j = 0
        while i < len(sections):
            section = sections[i]
            if i == 9:  # special case for shaders: must add entry for each material
                section = sections[i - 1]
            if section:
                f = Folder(binfile, self.SECTION_NAMES[i])
                for x in section:
                    assert x
                    f.add_entry(x.name)
                root_folders.append(f)
                binfile.create_ref(j, False)  # create the ref from stored offsets
                f.pack(binfile)
            else:
                root_folders.append(None)  # create placeholder
            i += 1
            j += 1
        return root_folders

    def build_texture_links(self, materials):
        # rebuild texture links
        texture_links = {}
        for x in materials:
            for y in x.layers:
                name = y.name
                if name not in texture_links:
                    texture_links[name] = 1
                else:
                    texture_links[name] += 1

        tex_links = [self.TextureLink(x, texture_links[x]) for x in texture_links]
        return tex_links

    def build_shaders(self, materials):
        shaders = self.shaders
        shader_mats = self.shader_mats
        for x in materials:
            shader = x.shader
            found = False
            for i in range(len(shaders)):
                if shader == shaders[i]:
                    shader_mats[i].append(x)
                    # This is to have the shader load the
                    # maximum number of layers necessary
                    if len(x.layers) > len(shaders[i].parent.layers):
                        shaders[i] = shader
                    found = True
                    break
            if not found:
                shader_mats.append([x])
                shaders.append(shader)
        return shaders

    def pre_pack(self, mdl0):
        """Cleans up references in preparation for packing"""
        sections = [None,
                    mdl0.bones,
                    mdl0.vertices,
                    mdl0.normals,
                    mdl0.colors,
                    mdl0.uvs,
                    None,
                    None,
                    mdl0.materials,
                    self.build_shaders(mdl0.materials),
                    mdl0.objects,
                    self.build_texture_links(mdl0.materials)
                    ]
        for i in range(1, len(sections) - 1):
            if sections[i]:
                rebuild_indexes(sections[i])
        sections[0] = self.build_definitions()
        return sections

    def build_definitions(self):
        mdl0 = self.node
        defs = [mdl0.NodeTree]
        if mdl0.NodeMix:
            defs.append(mdl0.NodeMix)
        opa = DrawList('DrawOpa', self)
        xlu = DrawList('DrawXlu', self)
        for poly in self.node.objects:
            mat = poly.material
            bone = poly.visible_bone
            is_xlu = mat.is_xlu()
            if not is_xlu:
                opa.add_entry(mat.index, poly.index, bone.index, poly.priority)
            else:
                xlu.add_entry(mat.index, poly.index, bone.index, poly.priority)
        if len(opa):
            opa.sort()
            defs.append(opa)
        if len(xlu):
            xlu.sort()
            defs.append(xlu)
        return defs

    def __init__(self, node, binfile):
        self.shaders = []
        self.shader_mats = []
        self.mat_packers = {}
        super().__init__(node, binfile)
