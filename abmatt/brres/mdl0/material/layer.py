""" Layer class """
from copy import copy

from abmatt.autofix import Bug, AutoFix
from abmatt.lib.matching import parseValStr, indexListItem, validBool, fuzzy_strings, it_eq
from abmatt.lib.node import Clipable


class Layer(Clipable):
    # ----------------------------------------------------------------------------
    #   Constants
    # ----------------------------------------------------------------------------
    SETTINGS = (
        "scale", "rotation", "translation", "scn0cameraref",
        "scn0lightref", "mapmode", "uwrap", "vwrap",
        "minfilter", "magfilter", "lodbias", "anisotrophy",
        "clampbias", "texelinterpolate", "projection", "inputform",
        "type", "coordinates", "embosssource", "embosslight",
        "normalize", "name")
    EXT = 'layr'
    WRAP = ("clamp", "repeat", "mirror")
    FILTER = ("nearest", "linear", "nearestmipmapnearest", "linearmipmapnearest", "nearestmipmaplinear",
              "linearmipmaplinear")
    ANISOTROPHY = ("one", "two", "four")
    MAPMODE = ("texcoord", "envcamera", "projection", "envlight", "envspec")
    PROJECTION = ("st", "stq")
    INPUTFORM = ("ab11", "abc1")
    TYPE = ("regular", "embossmap", "color0", "color1")
    COORDINATES = ("geometry", "normals", "colors", "binfileormalst", "binfileormalsb",
                   "texcoord0", "texcoord1", "texcoord2", "texcoord3", "texcoord4", "texcoord5", "texcoord6",
                   "texcoord7")
    MINFILTER_AUTO = False
    RENAME_UNKNOWN_REFS = True
    REMOVE_UNKNOWN_REFS = True

    def __init__(self, name, parent, binfile=None):
        """ Initializes, name, and parent material """
        self.enable_identity_matrix = True
        self.tex0_ref = None  # this can be filled with the reference to the brres texture
        self.texture_matrix = [1.0, 0, 0, 0,
                               0, 1.0, 0, 0,
                               0, 0, 1.0, 0]
        super(Layer, self).__init__(name, parent, binfile)

    def __eq__(self, other):
        """
        :type other: Layer
        :return: true if equal
        """
        return type(other) == Layer and self.enable == other.enable and self.name == other.name \
               and it_eq(self.scale, other.scale) \
               and self.rotation == other.rotation and it_eq(self.translation, other.translation) \
               and self.scn0_light_ref == other.scn0_light_ref and self.scn0_camera_ref == other.scn0_camera_ref \
               and self.map_mode == other.map_mode and self.vwrap == other.vwrap and self.uwrap == other.uwrap \
               and self.minfilter == other.minfilter and self.magfilter == other.magfilter \
               and self.lod_bias == other.lod_bias and self.max_anisotrophy == other.max_anisotrophy \
               and self.texel_interpolate == other.texel_interpolate and self.clamp_bias == other.clamp_bias \
               and self.normalize == other.normalize and self.projection == other.projection \
               and self.inputform == other.inputform and self.type == other.type \
               and self.coordinates == other.coordinates and self.emboss_source == other.emboss_source \
               and self.emboss_light == other.emboss_light

    def begin(self):
        self.enable = True
        self.scale = [1.0, 1.0]
        self.rotation = 0.0
        self.translation = [0.0, 0.0]
        self.scn0_light_ref = self.scn0_camera_ref = -1
        self.map_mode = 0
        self.vwrap = self.uwrap = 1
        self.minfilter = 1
        self.magfilter = 1
        self.lod_bias = 0.0
        self.max_anisotrophy = 0
        self.texel_interpolate = self.clamp_bias = False
        self.normalize = 0
        self.projection = 0
        self.inputform = 0
        self.type = 0
        self.coordinates = 5
        self.emboss_source = 5
        self.emboss_light = 0

    def __value__(self):
        return "Layer {}: scale {} rot {} trans {} uwrap {} vwrap {} minfilter {}".format(self.name,
                                                                                          self.scale, self.rotation,
                                                                                          self.translation, self.uwrap,
                                                                                          self.vwrap, self.minfilter)

    # ----------------------------------------------------------------------------------
    #   GETTERS
    # ----------------------------------------------------------------------------------
    def get_tex0(self, texture_map=None):
        if self.tex0_ref:
            return self.tex0_ref
        if texture_map is None:
            texture_map = self.get_texture_map()
            if texture_map is None:
                return None
        self.tex0_ref = texture_map.get(self.name)
        return self.tex0_ref

    def get_str(self, item):
        for i in range(len(self.SETTINGS)):
            if self.SETTINGS[i] == item:
                func = self.GET_SETTINGS[i]
                return func(self)

    def get_scale(self):
        return self.scale

    def get_rotation(self):
        return self.rotation

    def get_translation(self):
        return self.translation

    def get_scn0_light_ref(self):
        return self.scn0_light_ref

    def get_scn0_camera_ref(self):
        return self.scn0_camera_ref

    def get_map_mode(self):
        return self.MAPMODE[self.map_mode]

    def get_u_wrap(self):
        return self.WRAP[self.uwrap]

    def get_v_wrap(self):
        return self.WRAP[self.vwrap]

    def get_minfilter(self):
        return self.FILTER[self.minfilter]

    def get_magfilter(self):
        return self.FILTER[self.magfilter]

    def get_lod_bias(self):
        return self.lod_bias

    def get_anisotrophy(self):
        return self.ANISOTROPHY[self.max_anisotrophy]

    def get_clamp_bias(self):
        return self.clamp_bias

    def get_texel_interpolate(self):
        return self.texel_interpolate

    def get_projection(self):
        return self.PROJECTION[self.projection]

    def get_input_form(self):
        return self.INPUTFORM[self.inputform]

    def get_type(self):
        return self.TYPE[self.type]

    def get_coordinates(self):
        return self.COORDINATES[self.coordinates]

    def get_uv_channel(self):
        val = self.coordinates - 5
        return val if val >= 0 else None

    def get_emboss_light(self):
        return self.emboss_light

    def get_emboss_source(self):
        return self.emboss_source

    def get_normalize(self):
        return self.normalize

    def get_name(self):
        return self.name

    GET_SETTINGS = (get_scale, get_rotation, get_translation, get_scn0_camera_ref,
                    get_scn0_light_ref, get_map_mode, get_u_wrap, get_v_wrap, get_minfilter, get_magfilter,
                    get_lod_bias, get_anisotrophy, get_clamp_bias, get_texel_interpolate, get_projection,
                    get_input_form, get_type, get_coordinates, get_emboss_source, get_emboss_light,
                    get_normalize, get_name)

    def get_setter(self, key):
        for i in range(len(self.SETTINGS)):
            if self.SETTINGS[i] == key:
                return self.SET_SETTING[i]

    # ----------------------------------------------------------------------------------
    #   SETTERS
    # ----------------------------------------------------------------------------------

    def set_str(self, key, value):
        fun = self.get_setter(key)
        return fun(self, value)

    def set_x_scale(self, x_scale):
        val = float(x_scale)
        if self.scale[0] != val:
            self.scale = [val, self.scale[1]]
            self.mark_modified()

    def set_y_scale(self, x_scale):
        val = float(x_scale)
        if self.scale[1] != val:
            self.scale = [self.scale[0], val]
            self.mark_modified()

    def set_scale(self, scale):
        if self.scale != scale:
            self.scale = scale
            self.mark_modified()

    def set_scale_str(self, value):
        values = parseValStr(value)
        if len(values) < 2:
            raise ValueError("Scale requires 2 floats")
        self.set_scale((float(values[0]), float(values[1])))

    def set_rotation(self, rotation):
        if self.rotation != rotation:
            self.rotation = rotation
            self.mark_modified()

    def set_rotation_str(self, value):
        self.set_rotation(float(value))

    def set_x_translation(self, val):
        val = float(val)
        if val != self.translation[0]:
            self.translation = [val, self.translation[0]]
            self.mark_modified()

    def set_y_translation(self, val):
        val = float(val)
        if val != self.translation[1]:
            self.translation = [self.translation[0], val]
            self.mark_modified()

    def set_translation(self, translation):
        if self.translation != translation:
            self.translation = translation
            self.mark_modified()

    def set_translation_str(self, value):
        values = parseValStr(value)
        if len(values) < 2:
            raise ValueError("Translation requires 2 floats")
        self.set_translation((float(values[0]), float(values[1])))

    def set_camera_ref_str(self, value):
        i = int(value)
        if i != -1 and i != 0:
            raise ValueError("Expected -1 or 0 for camera reference")
        if self.scn0_camera_ref != i:
            self.scn0_camera_ref = i
            self.mark_modified()

    def set_light_ref_str(self, value):
        i = int(value)
        if i > 0:
            AutoFix.warn('{} set unusual light ref {}, expected -1'.format(self.name, value))
        if self.scn0_light_ref != i:
            self.scn0_light_ref = i
            self.mark_modified()

    def set_map_mode_str(self, value):
        i = indexListItem(self.MAPMODE, value, self.map_mode)
        if i >= 0:
            self.map_mode = i
            self.mark_modified()

    def set_u_wrap_str(self, value):
        i = indexListItem(self.WRAP, value, self.uwrap)
        if i >= 0:
            self.uwrap = i
            self.mark_modified()

    def set_v_wrap_str(self, value):
        i = indexListItem(self.WRAP, value, self.vwrap)
        if i >= 0:
            self.vwrap = i
            self.mark_modified()

    def set_minfilter_str(self, value):
        value = value.replace('_', '')
        i = indexListItem(self.FILTER, value, self.minfilter)
        if i >= 0:
            self.minfilter = i
            self.mark_modified()

    def set_magfilter_str(self, value):
        i = indexListItem(self.FILTER, value, self.magfilter)
        if i > 1:
            raise ValueError("MagFilter out of range (0-1)")
        elif i >= 0:
            self.magfilter = i
            self.mark_modified()

    def set_lod_bias_str(self, value):
        f = float(value)
        if f != self.lod_bias:
            self.lod_bias = f
            self.mark_modified()

    def set_anisotrophy_str(self, value):
        invalidI = False
        try:
            i = int(value)
            if i != 1 and i != 2 and i != 4:
                invalidI = True
            else:
                i -= 1
                if i > 2:
                    i = 2
        except ValueError:
            i = indexListItem(self.ANISOTROPHY, value, self.max_anisotrophy)
        if invalidI:
            raise ValueError("Invalid: '" + value + "', Anisotrophy expects 1|2|4")
        if i >= 0 and i != self.max_anisotrophy:
            self.max_anisotrophy = i
            self.mark_modified()

    def set_clamp_bias_str(self, value):
        val = validBool(value)
        if val != self.clamp_bias:
            self.clamp_bias = val
            self.mark_modified()

    def set_texel_interpolate_str(self, value):
        val = validBool(value)
        if val != self.texel_interpolate:
            self.texel_interpolate = val
            self.mark_modified()

    def set_projection_str(self, value):
        i = indexListItem(self.PROJECTION, value, self.projection)
        if i >= 0:
            self.projection = i
            self.mark_modified()

    def set_input_form_str(self, value):
        i = indexListItem(self.INPUTFORM, value, self.inputform)
        if i >= 0:
            self.inputform = i
            self.mark_modified()

    def set_type_str(self, value):
        i = indexListItem(self.TYPE, value, self.type)
        if i >= 0:
            self.type = i
            self.mark_modified()

    def set_coordinate_str(self, value):
        i = indexListItem(self.COORDINATES, value, self.coordinates)
        if i >= 0:
            self.coordinates = i
            self.mark_modified()

    def set_emboss_src_str(self, value):
        i = int(value)
        if not 0 <= i <= 7:
            raise ValueError("Value '" + value + "' out of range for emboss source")
        if self.emboss_source != i:
            self.emboss_source = i
            self.mark_modified()

    def set_emboss_light_str(self, value):
        i = int(value)
        if not 0 <= i <= 255:
            raise ValueError("Value '" + value + "' out of range for emboss light")
        if self.emboss_light != i:
            self.emboss_light = i
            self.mark_modified()

    def set_normalize_str(self, value):
        val = validBool(value)
        if val != self.normalize:
            self.normalize = val
            self.mark_modified()

    def set_layer_flags(self, nibble):
        """ from lsb, enable, scaledefault, rotationdefault, transdefault """
        self.enable = nibble & 1
        if nibble >> 1 & 1:
            self.scale = (1.0, 1.0)
        if nibble >> 2 & 1:
            self.rotation = 0.0
        if nibble >> 3 & 1:
            self.translation = (0.0, 0.0)
        return self.enable

    def set_name(self, value):
        self.rename(value)

    SET_SETTING = (set_scale_str, set_rotation_str, set_translation_str, set_camera_ref_str,
                   set_light_ref_str, set_map_mode_str, set_u_wrap_str, set_v_wrap_str, set_minfilter_str, set_magfilter_str,
                   set_lod_bias_str, set_anisotrophy_str, set_clamp_bias_str, set_texel_interpolate_str, set_projection_str,
                   set_input_form_str, set_type_str, set_coordinate_str, set_emboss_src_str, set_emboss_light_str,
                   set_normalize_str, set_name)

    def __str__(self):
        return self.name + ': srt:{} {} {}'.format(self.scale, self.rotation, self.translation)

    # -------------------------------------- PASTE ---------------------------
    def paste(self, item):
        if self.name == 'Null':
            self.set_name(item.name)
        self.uwrap = item.uwrap
        self.vwrap = item.vwrap
        self.minfilter = item.minfilter
        self.magfilter = item.magfilter
        self.lod_bias = item.lod_bias
        self.max_anisotrophy = item.max_anisotrophy
        self.clamp_bias = item.clamp_bias
        self.texel_interpolate = item.texel_interpolate
        self.scale = (item.scale[0], item.scale[1])
        self.rotation = item.rotation
        self.translation = (item.translation[0], item.translation[1])
        self.scn0_camera_ref = item.scn0_camera_ref
        self.scn0_light_ref = item.scn0_light_ref
        self.map_mode = item.map_mode
        self.enable_identity_matrix = item.enable_identity_matrix
        self.texture_matrix = copy(item.texture_matrix)
        self.projection = item.projection
        self.inputform = item.inputform
        self.type = item.type
        self.coordinates = item.coordinates
        self.emboss_source = item.emboss_source
        self.emboss_light = item.emboss_light
        self.normalize = item.normalize
        self.mark_modified()

    def info(self, key=None, indentation_level=0):
        trace = '  ' * indentation_level + self.name if indentation_level else '>' + self.parent.name + "->" + self.name
        if key:
            val = self.get_str(key)
            AutoFix.info("{}\t{}:{}".format(trace, key, val), 1)
        else:
            AutoFix.info("{}:\tScale:{} Rot:{} Trans:{}".format(
                trace, self.scale, self.rotation, self.translation), 1)

    def uses_mipmaps(self):
        return self.minfilter > 1

    def set_minfilter(self, value):
        if self.minfilter != value:
            self.minfilter = value
            self.mark_modified()

    def check(self, texture_map=None):
        # check if we have texture map
        if texture_map is None:
            texture_map = self.get_texture_map()
            if texture_map is None:
                return
        tex = texture_map.get(self.name)
        if not tex:
            # check if we have some reference
            if self.tex0_ref:
                if texture_map:  # add the texture if it's not in the map
                    self.parent.getBrres().add_tex0(self.tex0_ref)
                tex = self.tex0_ref
        else:
            self.tex0_ref = tex
        if not tex:
            # try fuzz
            result = None
            b = Bug(2, 3, 'No texture matching {}'.format(self.name), '')
            if self.RENAME_UNKNOWN_REFS:
                result = fuzzy_strings(self.name, texture_map)
                if result is not None:
                    b.fix_des = 'Rename to {}'.format(result)
                    self.rename(result)
                    b.resolve()
                    tex = texture_map.get(self.name)
                    self.mark_modified()
            if result is None:
                if self.REMOVE_UNKNOWN_REFS:
                    b.fix_des = 'Remove reference'
                    self.parent.remove_layer(self.name)
                    b.resolve()
                    self.mark_modified()
                    return
        if tex:
            if self.uses_mipmaps():
                if tex.num_mips == 0:
                    b = Bug(4, 4, '{} no mipmaps in tex0'.format(self.name), 'Set minfilter to linear')
                    if self.MINFILTER_AUTO:
                        self.set_minfilter(1)  # linear
                        b.resolve()
                        self.mark_modified()
            else:
                if tex.num_mips > 0:
                    b = Bug(4, 4, '{} mipmaps disabled but TEX0 has {}'.format(
                        self.name, tex.num_mips), 'Set minfilter to LinearMipmapLinear')
                    if self.MINFILTER_AUTO:
                        self.set_minfilter(5)  # linearmipmaplinear
                        b.resolve()
                        self.mark_modified()
