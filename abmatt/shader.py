# ------------------------------------------------------------------------
#   Shader Class
# ------------------------------------------------------------------------
from copy import deepcopy, copy

from abmatt.binfile import Folder
from abmatt.matching import *
from abmatt.wiigraphics.bp import RAS1_IRef, BPCommand, KCel, ColorEnv, AlphaEnv, IndCmd, RAS1_TRef


class ShaderList():
    """For maintaining shader collections"""
    FOLDER = "Shaders"

    def __init__(self):
        self.list = []  # shaders

    def __len__(self):
        return len(self.list)

    def __getitem__(self, item):
        return self.list[item]

    def __setitem__(self, key, value):
        self.list[key] = value

    def splitShaderOnMaterials(self, shader, material_list):
        """Splits the shader based on the materials in material list"""
        new_shader = deepcopy(shader)
        self.list.append(new_shader)
        i = 0
        newMats = []
        oldMats = []
        for x in shader.materials:
            if x in material_list:
                newMats.append(x)
                x.shader = new_shader
            else:
                oldMats.append(x)
                # x.shader = shader
        shader.materials = oldMats
        new_shader.materials = newMats
        return new_shader

    def getShaders(self, material_list, for_modification=True):
        """Gets the shaders, if for modification possibly splitting/creating new ones as necessary"""
        shaders = []
        for m in material_list:
            sh = m.shader
            if sh not in shaders:  # need to add shader?
                if not for_modification:
                    shaders.append(sh)
                else:
                    is_split = False
                    for shader_mat in sh.materials:
                        if shader_mat not in material_list:  # needs split?
                            is_split = True
                            shaders.append(self.splitShaderOnMaterials(sh, material_list))
                            break
                    if not is_split:
                        shaders.append(sh)
        return shaders

    def consolidate(self):
        """Removes duplicate shaders"""
        li = self.list
        i = 0
        while i < len(li) - 1:
            x = li[i]
            j = i + 1
            while j < len(li):
                if x == li[j]:
                    sh = li.pop(j)
                    x.materials.extend(sh.materials)
                    for mat in sh.materials:
                        mat.shader = x
                else:
                    j += 1
            i += 1

    @staticmethod
    def hookMatsToShaders(shader_offsets, materials):
        """Hooks up materials to shaders based on the shader offset
        :param shader_offsets: the offset:shader map created during unpacking
        :param materials: the model materials
        """
        for mat in materials:
            shader = shader_offsets[mat.shaderOffset]
            mat.shader = shader
            shader.materials.append(mat)

    def unpack(self, binfile):
        binfile.recall()  # from offset header
        folder = Folder(binfile, self.FOLDER)
        folder.unpack(binfile)
        list = self.list
        offsets = {}  # for tracking the shaders we've unpacked
        while len(folder.entries):
            name = folder.recallEntryI()
            if not binfile.offset in offsets:
                d = Shader(name, self)
                offsets[binfile.offset] = d
                d.unpack(binfile)
                list.append(d)
        return offsets

    def pack(self, binfile, folder):
        """Packs the shader data, generating material and index group references"""
        li = self.list
        for i in range(len(li)):
            x = li[i]
            for m in x.materials:
                folder.createEntryRef(m.name)  # create index group reference
                binfile.createRefFrom(m.offset)  # create the material shader reference
            x.pack(binfile, i)


class Stage():
    """ Single shader stage """
    # COLOR STRINGS
    RASTER_COLORS = ("lightchannel0", "lightchannel1", "bumpalpha", "normalizedbumpalpha", "zero")
    COLOR_CONSTANTS = ("1_1", "7_8", "3_4", "5_8", "1_2", "3_8", "1_4", "1_8",
                       "color0_rgb", "color1_rgb", "color2_rgb", "color3_rgb",
                       "color0_rrr", "color1_rrr", "color2_rrr", "color3_rrr",
                       "color0_ggg", "color1_ggg", "color2_ggg", "color3_ggg",
                       "color0_bbb", "color1_bbb", "color2_bbb", "color3_bbb",
                       "color0_aaa", "color1_aaa", "color2_aaa", "color3_aaa")
    COLOR_SELS = ("outputcolor", "outputalpha", "color0", "alpha0", "color1",
                  "alpha1", "color2", "alpha2", "texturecolor", "texturealpha",
                  "rastercolor", "rasteralpha", "one", "half",
                  "colorselection", "zero")
    BIAS = ("zero", "addhalf", "subhalf")
    OPER = ("add", "subtract")
    SCALE = ("multiplyby1", "multiplyby2", "multiplyby4", "divideby2")
    SCALEN = (1, 2, 4, 1 / 2)
    COLOR_DEST = ("outputcolor", "color0", "color1", "color2")

    # ALPHA
    ALPHA_CONSTANTS = ("1_1", "7_8", "3_4", "5_8", "1_2", "3_8", "1_4", "1_8",
                       "color0_red", "color1_red", "color2_red", "color3_red",
                       "color0_green", "color1_green", "color2_green", "color3_green",
                       "color0_blue", "color1_blue", "color2_blue", "color3_blue",
                       "color0_alpha", "color1_alpha", "color2_alpha", "color3_alpha")
    ALPHA_SELS = ("outputalpha", "alpha0", "alpha1", "alpha2", "texturealpha",
                  "rasteralpha", "alphaselection", "zero")
    ALPHA_DEST = ("outputalpha", "alpha0", "alpha1", "alpha2")

    # INDIRECT TEVS
    TEX_FORMAT = ("f_8_bit_offsets", "f_5_bit_offsets", "f_4_bit_offsets", "f_3_bit_offsets")
    IND_BIAS = ("none", "s", "t", "st", "u", "su", "tu", "stu")
    IND_ALPHA = ("off", "s", "t", "u")
    IND_MATRIX = ("nomatrix", "matrix0", "matrix1", "matrix2", "matrixs0",
                  "matrixs1", "matrixs2", "matrixt0", "matrixt1", "matrixt2")
    WRAP = ("nowrap", "wrap256", "wrap128", "wrap64", "wrap16", "wrap0")
    SETTINGS = ("enabled", "mapid", "coordinateid",
                "textureswapselection", "rastercolor",
                "rasterswapselection",
                "colorconstantselection", "constantcolorselection", "colora",
                "colorb", "colorc",
                "colord", "colorbias",
                "coloroperation", "colorclamp",
                "colorscale", "colordestination",
                "constantalphaselection", "alphaconstantselection", "alphaa",
                "alphab", "alphac",
                "alphad", "alphabias",
                "alphaoperation", "alphaclamp",
                "alphascale", "alphadestination",
                "indirectstage", "indirectformat",
                "indirectalpha",
                "indirectbias", "indirectmatrix",
                "indirectswrap", "indirecttwrap",
                "indirectuseprevstage", "indirectunmodifiedlod")

    def __init__(self, id, parent):
        self.id = id
        self.parent = parent
        self.map = {
            "enabled": True, "mapid": id, "coordinateid": id,
            "textureswapselection": 0, "rastercolor": self.RASTER_COLORS[4],
            "rasterswapselection": 0,
            "colorconstantselection": self.COLOR_CONSTANTS[8], "colora": self.COLOR_SELS[-1],
            "colorb": self.COLOR_SELS[8], "colorc": self.COLOR_SELS[10],
            "colord": self.COLOR_SELS[-1], "colorbias": self.BIAS[0],
            "coloroperation": self.OPER[0], "colorclamp": True,
            "colorscale": self.SCALE[0], "colordestination": self.COLOR_DEST[0],
            "alphaconstantselection": self.ALPHA_CONSTANTS[20], "alphaa": self.ALPHA_SELS[-1],
            "alphab": self.ALPHA_SELS[4], "alphac": self.ALPHA_SELS[5],
            "alphad": self.ALPHA_SELS[1], "alphabias": self.BIAS[0],
            "alphaoperation": self.OPER[0], "alphaclamp": True,
            "alphascale": self.SCALE[0], "alphadestination": self.ALPHA_DEST[0],
            "indirectstage": 0, "indirectformat": self.TEX_FORMAT[0],
            "indirectalpha": self.IND_ALPHA[0],
            "indirectbias": self.IND_BIAS[0], "indirectmatrix": self.IND_MATRIX[0],
            "indirectswrap": self.WRAP[0], "indirecttwrap": self.WRAP[0],
            "indirectuseprevstage": False, "indirectunmodifiedlod": False
        }

    def __eq__(self, stage):
        """Determines if stages are equal"""
        return self.id == stage.id and self.map == stage.map

    def __str__(self):
        return str(self.map)

    def __getitem__(self, key):
        i = key.find('constant')
        if 0 <= i < 5:  # out of order
            is_alpha = True if 'alpha' in key else False
            if is_alpha:
                key = 'alphaconstantselection'
            else:
                key = 'colorconstantselection'
        if key not in self.map:
            raise ValueError("No such shader stage setting {} possible keys are: \n\t{}".format(key, self.map.keys()))
        return self.map[key]

    def info(self, key=None, indentation_level=0):
        trace = '  ' * indentation_level if indentation_level else '>' + str(self.parent.getMaterialNames())
        if key:
            print('{}->Stage{}: {}:{}'.format(trace, self.id, key, self[key]))
        else:
            print('{}Stage{}: MapId:{} CoordinateId:{} ColorScale:{} ColorDestination:{}'.format(
                trace, self.id, self['mapid'], self['coordinateid'],
                self['colorscale'], self['colordestination']))

    def getRasterColorI(self):
        i = self.RASTER_COLORS.index(self.map["rastercolor"])
        if i > 1:
            i += 3
        return i

    def setRasterColorI(self, i):
        if i > 1:
            i -= 3
        self.map["rastercolor"] = self.RASTER_COLORS[i]

    def getConstantAlphaI(self):
        i = self.ALPHA_CONSTANTS.index(self.map["alphaconstantselection"])
        if i > 7:
            return i + 8
        return i

    def setConstantAlphaI(self, i):
        if i > 7:
            i -= 8
        self.map["alphaconstantselection"] = self.ALPHA_CONSTANTS[i]

    def getIndMtxI(self):
        i = self.IND_MATRIX.index(self.map["indirectmatrix"])
        if i > 3:
            i += 1
        if i > 7:
            i += 1
        return i

    def setIndTexMtxI(self, i):
        if i > 8:
            i -= 1
        if i > 4:
            i -= 1
        self.map["indirectmatrix"] = self.IND_MATRIX[i]

    def getConstantColorI(self):
        i = self.COLOR_CONSTANTS.index(self.map["colorconstantselection"])
        if i > 7:
            return i + 4
        return i

    def setConstantColorI(self, index):
        if index >= 0xc:
            index -= 4
        self.map["colorconstantselection"] = self.COLOR_CONSTANTS[index]

    def __setitem__(self, key, value):
        i = key.find('constant')
        is_alpha = True if 'alpha' in key else False
        if 0 <= i < 5:  # out of order
            if is_alpha:
                key = 'alphaconstantselection'
            else:
                key = 'colorconstantselection'
        if not key in self.map:
            raise ValueError("No such shader stage setting {} possible keys are: \n\t{}".format(key, self.map.keys()))
        # bools
        if key == "enabled" or "clamp" in key or key == "indirectuseprevstage" \
                or key == "indirectunmodifiedlod":
            self.map[key] = validBool(value)
        # ints
        elif "swap" in key or "stage" in key:
            self.map[key] = validInt(value, 0, 4)
        elif "id" in key:
            self.map[key] = validInt(value, 0, 7)
        else:  # list indexing ones
            value = value.replace('constant', '')
            if "scale" in key:
                try:
                    f = validFloat(value, 0.5, 4)
                    pos = indexListItem(self.SCALEN, f)
                    value = self.SCALE[pos]
                except:
                    indexListItem(self.SCALE, value)
            elif "color" in key:
                if len(key) < 7:  # abcd
                    if value == '0':
                        value = 'zero'
                    elif value == '1':
                        value = 'one'
                    elif value == '0.5':
                        value = 'half'
                    else:
                        indexListItem(self.COLOR_SELS, value)
                elif key == "colorconstantselection":
                    value = value.replace('constant', '')
                    indexListItem(self.COLOR_CONSTANTS, value)
                elif key == "colordestination":
                    indexListItem(self.COLOR_DEST, value)
                elif key == "colorbias":
                    indexListItem(self.BIAS, value)
                elif key == "coloroperation":
                    indexListItem(self.OPER, value)
                elif key == "rastercolor":
                    if value == '0':
                        value = 'zero'
                    else:
                        indexListItem(self.RASTER_COLORS, value)
            elif is_alpha:
                if len(key) < 7:  # abcd
                    if value == '0':
                        value = 'zero'

                    else:
                        indexListItem(self.ALPHA_SELS, value)
                elif key == "alphaconstantselection":
                    value = value.replace('constant', '')
                    indexListItem(self.ALPHA_CONSTANTS, value)
                elif key == "alphadestination":
                    indexListItem(self.ALPHA_DEST, value)
                elif key == "alphabias":
                    indexListItem(self.BIAS, value)
                elif key == "alphaoperation":
                    indexListItem(self.OPER, value)
            elif "indirect" in key:
                if key == "indirectformat":
                    indexListItem(self.TEX_FORMAT, value)
                elif key == "indirectmatrix":
                    indexListItem(self.IND_MATRIX, value)
                elif key == "indirectalpha":
                    indexListItem(self.IND_ALPHA, value)
                elif key == "indirectbias":
                    indexListItem(self.IND_BIAS, value)
                elif "wrap" in key:
                    indexListItem(self.WRAP, value)
            self.map[key] = value

    def unpackColorEnv(self, binfile):
        """ Unpacks the color env """
        ce = ColorEnv(self.id)
        ce.unpack(binfile)
        self.map["colora"] = self.COLOR_SELS[ce.getSelA()]
        self.map["colorb"] = self.COLOR_SELS[ce.getSelB()]
        self.map["colorc"] = self.COLOR_SELS[ce.getSelC()]
        self.map["colord"] = self.COLOR_SELS[ce.getSelD()]
        self.map["colorbias"] = self.BIAS[ce.getBias()]
        self.map["coloroperation"] = self.OPER[ce.getSub()]
        self.map["colorclamp"] = ce.getClamp()
        self.map["colorscale"] = self.SCALE[ce.getShift()]
        self.map["colordestination"] = self.COLOR_DEST[ce.getDest()]

    def unpackAlphaEnv(self, binfile):
        ''' Unpacks alpha env '''
        ae = AlphaEnv(self.id)
        ae.unpack(binfile)
        self.map["alphaa"] = self.ALPHA_SELS[ae.getSelA()]
        self.map["alphab"] = self.ALPHA_SELS[ae.getSelB()]
        self.map["alphac"] = self.ALPHA_SELS[ae.getSelC()]
        self.map["alphad"] = self.ALPHA_SELS[ae.getSelD()]
        self.map["alphabias"] = self.BIAS[ae.getBias()]
        self.map["alphaoperation"] = self.OPER[ae.getSub()]
        self.map["alphaclamp"] = ae.getClamp()
        self.map["alphascale"] = self.SCALE[ae.getShift()]
        self.map["alphadestination"] = self.ALPHA_DEST[ae.getDest()]
        self.map["textureswapselection"] = ae.getTSwap()
        self.map["rasterswapselection"] = ae.getRSwap()

    def unpackIndirect(self, binfile):
        c = IndCmd(self.id)
        c.unpack(binfile)
        self.map["indirectstage"] = c.getStage()
        self.map["indirectformat"] = self.TEX_FORMAT[c.getFormat()]
        self.map["indirectbias"] = self.IND_BIAS[c.getBias()]
        self.setIndTexMtxI(c.getMtx())
        self.map["indirectswrap"] = self.WRAP[c.getSWrap()]
        self.map["indirecttwrap"] = self.WRAP[c.getTWrap()]
        self.map["indirectalpha"] = self.IND_ALPHA[c.getAlpha()]
        self.map["indirectuseprevstage"] = c.getUsePrevStage()
        self.map["indirectunmodifiedlod"] = c.getUnmodifiedLOD()

    def packColorEnv(self, binfile):
        ce = ColorEnv(self.id)
        a = self.COLOR_SELS.index(self["colora"])
        b = self.COLOR_SELS.index(self["colorb"])
        c = self.COLOR_SELS.index(self["colorc"])
        d = self.COLOR_SELS.index(self["colord"])
        bi = self.BIAS.index(self["colorbias"])
        op = self.OPER.index(self["coloroperation"])
        sc = self.SCALE.index(self["colorscale"])
        dest = self.COLOR_DEST.index(self["colordestination"])
        ce.data = dest << 22 | sc << 20 | self["colorclamp"] << 19 | op << 18 \
                  | bi << 16 | a << 12 | b << 8 | c << 4 | d
        ce.pack(binfile)

    def packAlphaEnv(self, binfile):
        ae = AlphaEnv(self.id)
        a = self.ALPHA_SELS.index(self["alphaa"])
        b = self.ALPHA_SELS.index(self["alphab"])
        c = self.ALPHA_SELS.index(self["alphac"])
        d = self.ALPHA_SELS.index(self["alphad"])
        bi = self.BIAS.index(self["alphabias"])
        op = self.OPER.index(self["alphaoperation"])
        sc = self.SCALE.index(self["alphascale"])
        dest = self.ALPHA_DEST.index(self["alphadestination"])
        ae.data = dest << 22 | sc << 20 | self["alphaclamp"] << 19 | op << 18 \
                  | bi << 16 | a << 13 | b << 10 | c << 7 | d << 4 \
                  | self["textureswapselection"] << 2 | self["rasterswapselection"]
        ae.pack(binfile)

    def packIndirect(self, binfile):
        c = IndCmd(self.id)
        f = self.TEX_FORMAT.index(self["indirectformat"])
        b = self.IND_BIAS.index(self["indirectbias"])
        a = self.IND_ALPHA.index(self["indirectalpha"])
        m = self.getIndMtxI()
        sw = self.WRAP.index(self["indirectswrap"])
        tw = self.WRAP.index(self["indirecttwrap"])
        c.data = self["indirectunmodifiedlod"] << 20 | self["indirectuseprevstage"] << 19 \
                 | tw << 16 | sw << 13 | m << 9 | a << 7 | b << 4 | f << 2 \
                 | self["indirectstage"]
        c.pack(binfile)


class Shader():
    BYTESIZE = 512
    # Uses a constant swap table - todo track swap table?
    SWAP_MASK = BPCommand(0xFE, 0xF)
    SWAP_TABLE = (BPCommand(0xF6, 0x4), BPCommand(0xF7, 0xE), BPCommand(0xF8, 0x0),
                  BPCommand(0xF9, 0xC), BPCommand(0xFA, 0x5), BPCommand(0xFB, 0xD),
                  BPCommand(0xFC, 0xA), BPCommand(0xFD, 0xE))
    SEL_MASK = BPCommand(0xFE, 0xFFFFF0)
    SETTINGS = ('texturerefcount', 'indirectmap', 'indirectcoord', 'stagecount')

    def __init__(self, name, parent):
        self.parent = parent
        self.name = name
        self.stages = []
        self.swap_table = deepcopy(self.SWAP_TABLE)
        self.materials = []  # materials to be hooked
        self.texRefCount = 1  # Number of texture references
        self.indTexMaps = [-1] * 4
        self.indTexCoords = [-1] * 4

    def __eq__(self, other):
        if self.texRefCount != other.texRefCount or len(self.stages) != len(other.stages) or \
                len(self.indTexMaps) != len(other.indTexMaps) or len(self.indTexCoords) != len(self.indTexCoords):
            return False
        my_stages = self.stages
        others = other.stages
        for i in range(len(my_stages)):
            if my_stages[i] != others[i]:
                return False
        for i in range(len(self.indTexMaps)):
            if self.indTexMaps[i] != other.indTexMaps[i]:
                return False
        for i in range(len(self.indTexCoords)):
            if self.indTexCoords[i] != other.indTexCoords[i]:
                return False
        return True

    def getIndirectMatricesUsed(self):
        matrices_used = [False] * 3
        for x in self.stages:
            matrix = x['indirectmatrix'][-1]
            if matrix.isdigit():
                matrices_used[int(matrix)] = True
        return matrices_used

    def detect_unusedMapId(self):
        """Attempts to find next available unused mapid"""
        used = [x['mapid'] for x in self.stages]
        for i in range(16):
            if i not in used and i not in self.indTexMaps:
                return i
        return 0

    @staticmethod
    def detectIndirectIndex(key):
        i = 0 if not key[-1].isdigit() else int(key[-1])
        if not 0 <= i < 4:
            raise ValueError('Indirect index {} out of range (0-3).'.format(i))
        return i

    def __getitem__(self, key):
        if self.SETTINGS[0] == key:
            return self.texRefCount
        elif self.SETTINGS[1] in key:
            return self.indTexMaps[self.detectIndirectIndex(key)]
        elif self.SETTINGS[2] in key:
            return self.indTexCoords[self.detectIndirectIndex(key)]
        elif self.SETTINGS[3] == key:  # stage count
            return len(self.stages)

    def __setitem__(self, key, value):
        value = validInt(value, 0, 8)
        if self.SETTINGS[0] == key:  # texture refs
            self.texRefCount = value
        elif self.SETTINGS[1] in key:  # indirect map
            self.indTexMaps[self.detectIndirectIndex(key)] = value
        elif self.SETTINGS[2] in key:  # indirect coord
            self.indTexCoords[self.detectIndirectIndex(key)] = value
        elif self.SETTINGS[3] == key:   # stage count
            current_len = len(self.stages)
            if current_len < value:
                while current_len < value:
                    self.addStage()
                    current_len += 1
                self.onUpdateActiveStages(current_len)
            elif current_len > value:
                while current_len > value:
                    self.removeStage()
                    current_len -= 1
                self.onUpdateActiveStages(current_len)

    def getMaterialNames(self):
        return [mat.name for mat in self.materials]

    def info(self, key=None, indentation_level=0):
        trace = '  ' * indentation_level if indentation_level else '>'
        if not key:
            print('{}Shader{}: {} stages, IndirectMap {} IndirectCoord {}'.format(trace,
                                                                                  self.getMaterialNames(),
                                                                                  len(self.stages),
                                                                                  self.indTexMaps,
                                                                                  self.indTexCoords))
            indentation_level += 1
            for x in self.stages:
                x.info(key, indentation_level)
        else:
            print('{}{}: {}:{} '.format(trace, self.getMaterialNames(), key, self[key]))

    def getStage(self, n):
        if not 0 <= n < len(self.stages):
            # todo: add shader stage?
            raise ValueError("Shader stage {} out of range, has {} stages".format(n, len(self.stages)))
        return self.stages[n]

    def addStage(self):
        """Adds stage to shader"""
        stages = self.stages
        s = Stage(len(stages), self)
        mapid = self.detect_unusedMapId()
        s['mapid'] = mapid
        s['coordinateid'] = mapid
        stages.append(s)
        return s

    def onUpdateActiveStages(self, num_stages):
        for x in self.materials:
            x.shaderStages = num_stages

    def removeStage(self, id=-1):
        if len(self.stages) == 1:
            raise Exception('Shader must have at least 1 stage')
        self.stages.pop(id)

    def __deepcopy__(self, memodict=None):
        ret = Shader(self.name, self.parent)
        for x in self.stages:
            s = Stage(x.id, ret)
            map = s.map
            for key, val in x.map.items():
                map[key] = val
            ret.stages.append(s)
        ret.texRefCount = self.texRefCount
        ret.indTexMaps = copy(self.indTexMaps)
        ret.indTexCoords = copy(self.indTexCoords)
        return ret

    def unpack(self, binfile):
        """ Unpacks shader TEV """
        binfile.start()
        length, outer, id, stage_count, res0, res1, res2, = binfile.read("3I4B", 16)
        layer_indices = binfile.read("8B", 8)
        self.texRefCount = 0
        for x in layer_indices:
            if x > 10:
                break
            self.texRefCount += 1
        assert (stage_count <= 16)
        self.stages = []
        for i in range(stage_count):
            self.stages.append(Stage(len(self.stages), self))

        binfile.advance(8)
        kcel = KCel(0)
        tref = RAS1_TRef(0)
        for x in self.swap_table:
            binfile.advance(5)  # skip extra masks
            x.unpack(binfile)
        iref = RAS1_IRef()
        iref.unpack(binfile)
        for i in range(4):
            x = iref.getTexMap(i)
            self.indTexMaps[i] = x
            y = iref.getTexCoord(i)
            self.indTexCoords[i] = y
        binfile.align()
        i = 0
        while i < stage_count:
            stage0 = self.stages[i]
            i += 1
            if i < stage_count:
                stage1 = self.stages[i]
                i += 1
            else:
                stage1 = None
            binfile.advance(5)  # skip mask
            kcel.unpack(binfile)
            # print("Color Selection index {}, data {}".format(kcel.getCSel0(), kcel.data))
            # print("Alpha Selection index {}".format(kcel.getASel0()))
            tref.unpack(binfile)
            stage0.map["enabled"] = tref.getTexEnabled0()
            stage0.map["mapid"] = tref.getTexMapID0()
            stage0.map["coordinateid"] = tref.getTexCoordID0()
            stage0.setConstantColorI(kcel.getCSel0())
            stage0.setConstantAlphaI(kcel.getASel0())
            stage0.setRasterColorI(tref.getColorChannel0())
            stage0.unpackColorEnv(binfile)
            if stage1:
                stage1.map["enabled"] = tref.getTexEnabled1()
                stage1.map["mapid"] = tref.getTexMapID1()
                stage1.map["coordinateid"] = tref.getTexCoordID1()
                stage1.setConstantColorI(kcel.getCSel1())
                stage1.setConstantAlphaI(kcel.getASel1())
                stage1.setRasterColorI(tref.getColorChannel1())
                stage1.unpackColorEnv(binfile)
            else:
                binfile.advance(5)  # skip unpack color env
            stage0.unpackAlphaEnv(binfile)
            if stage1:
                stage1.unpackAlphaEnv(binfile)
            else:
                binfile.advance(5)
            stage0.unpackIndirect(binfile)
            if stage1:
                stage1.unpackIndirect(binfile)
            else:
                binfile.advance(5)
            binfile.align(16)
        binfile.advanceAndEnd(self.BYTESIZE)

    def pack(self, binfile, id):
        """ Packs the shader """
        binfile.start()
        binfile.write("IiI4B", self.BYTESIZE, binfile.getOuterOffset(), id,
                      len(self.stages), 0, 0, 0)
        layer_indices = [0xff] * 8
        for i in range(self.texRefCount):
            layer_indices[i] = i
        binfile.write("8B", *layer_indices)
        binfile.align()
        for kcel in self.swap_table:
            self.SWAP_MASK.pack(binfile)
            kcel.pack(binfile)
        # Construct indirect data
        iref = RAS1_IRef()
        data = 0
        for i in range(3, -1, -1):
            data <<= 3
            data |= self.indTexCoords[i] & 7
            data <<= 3
            data |= self.indTexMaps[i] & 7
        iref.data = data
        iref.pack(binfile)
        binfile.align()
        i = j = 0
        while i < len(self.stages):
            stage0 = self.stages[i]
            i += 1
            if i < len(self.stages):
                stage1 = self.stages[i]
                i += 1
            else:
                stage1 = None
            self.SEL_MASK.pack(binfile)
            kcel = KCel(j)  # KCEL
            cc = stage0.getConstantColorI()
            ac = stage0.getConstantAlphaI()
            kcel.data = cc << 4 | ac << 9
            if stage1:
                cc = stage1.getConstantColorI()
                ac = stage1.getConstantAlphaI()
                kcel.data |= cc << 14 | ac << 19
            kcel.pack(binfile)
            # TREF
            tref = RAS1_TRef(j)
            cc = stage0.getRasterColorI()
            tref.data = cc << 7 | stage0["enabled"] << 6 | stage0["coordinateid"] << 3 \
                        | stage0["mapid"]
            if stage1:
                cc = stage1.getRasterColorI()
                tref.data |= cc << 19 | stage1["enabled"] << 18 \
                             | stage1["coordinateid"] << 15 | stage1["mapid"] << 12
            else:
                tref.data |= 0x3bf000
            tref.pack(binfile)
            # all the rest
            stage0.packColorEnv(binfile)
            if stage1:
                stage1.packColorEnv(binfile)
            else:
                binfile.advance(5)
            stage0.packAlphaEnv(binfile)
            if stage1:
                stage1.packAlphaEnv(binfile)
            else:
                binfile.advance(5)
            stage0.packIndirect(binfile)
            if stage1:
                stage1.packIndirect(binfile)
            else:
                binfile.advance(5)
            j += 1
        binfile.advanceAndEnd(self.BYTESIZE)

    def __str__(self):
        return "shdr layers {} stages {}: {}".format(len(self.stages), self.countDirectStages(),
                                                     self.countIndirectStages())

    def countDirectStages(self):
        i = 0
        for x in self.stages:
            # print("Ref {} is {}".format(i, x))
            if x > 7:
                break
            i += 1
        return i

    def countIndirectStages(self):
        i = 0
        for x in self.indTexCoords:
            if x >= 7:
                break
            i += 1
        return i

# possibly try to fix ctools bugs later
# class TexCoord:
#     TEX_FORMAT = ("u8", "s8", "u16", "s16", "float")
#     def __init__(self, file):
#         self.offset = file.offset
#         data = file.read(Struct("> I i 5I 2B H 2f 2f"), 0x30)
#         # print("Texture header: {}".format(data))
#         self.length = data[0]
#         self.mdl0Offset = data[1]
#         self.dataOffset = data[2]
#         self.nameOffset = data[3]
#         self.id = data[4]
#         self.component = data[5]
#         self.format = data[6]
#         self.divisor = data[7]
#         self.stride = data[8]
#         self.size = data[9]
#         self.minimum = data[10:12]
#         self.maximum = data[12:14]
#         file.offset = self.offset + self.dataOffset
#         data = file.read(Struct("> " + color_str(self.length - 0x30) + "B"), self.length - 0x30)
#         # print("TCoord: {}".format(data))
#
#     def __str__(self):
#         return "UV {} size {} format {} divisor {} stride {}".format(self.id, self.size, self.TEX_FORMAT[self.format], self.divisor, self.stride)