import json

from abmatt.brres.lib.matching import splitKeyVal, validBool, parse_color, indexListItem, it_eq


class LightChannel:
    LC_ERROR = 'Invalid Light "{}", Expected ((color|alpha)control:key:value|[material|ambient|raster]\
(color|alpha)(enable|rgba))'

    def __init__(self, unpacking=False):
        if not unpacking:
            self.begin()

    def __eq__(self, other):
        """
        :type other: LightChannel
        :return: True if equal
        """
        return type(other) == LightChannel and self.materialColorEnabled == other.materialColorEnabled and \
            self.materialAlphaEnabled == other.materialAlphaEnabled and \
            self.ambientAlphaEnabled == other.ambientAlphaEnabled and \
            self.ambientColorEnabled == other.ambientColorEnabled and \
            self.rasterAlphaEnabled == other.rasterAlphaEnabled and \
            self.rasterColorEnabled == other.rasterColorEnabled and \
            it_eq(self.materialColor, other.materialColor) and \
            it_eq(self.ambientColor, other.ambientColor) and \
            self.colorLightControl == other.colorLightControl and \
            self.alphaLightControl == other.alphaLightControl

    def begin(self):
        self.materialColorEnabled = self.materialAlphaEnabled = True
        self.ambientAlphaEnabled = self.ambientColorEnabled = True
        self.rasterAlphaEnabled = self.rasterColorEnabled = True
        self.materialColor = [128, 128, 128, 255]
        self.ambientColor = [0, 0, 0, 255]
        self.colorLightControl = self.LightChannelControl(0x700)
        self.alphaLightControl = self.LightChannelControl(0x700)
        return self

    def to_json(self):
        return {
            'materialColorEnabled': self.materialColorEnabled,
            'materialAlphaEnabled': self.materialAlphaEnabled,
            'ambientColorEnabled': self.ambientColorEnabled,
            'ambientAlphaEnabled': self.ambientAlphaEnabled,
            'rasterColorEnabled': self.rasterColorEnabled,
            'rasterAlphaEnabled': self.rasterAlphaEnabled,
            'materialColor': self.materialColor,
            'ambientColor': self.ambientColor,
            'colorLightControl': self.colorLightControl.to_json(),
            'alphaLightControl': self.alphaLightControl.to_json()
        }

    def parse_json(self, x):
        self.materialColorEnabled = x['materialColorEnabled']
        self.materialAlphaEnabled = x['materialAlphaEnabled']
        self.ambientColorEnabled = x['ambientColorEnabled']
        self.ambientAlphaEnabled = x['ambientAlphaEnabled']
        self.rasterColorEnabled = x['rasterColorEnabled']
        self.rasterAlphaEnabled = x['rasterAlphaEnabled']
        self.materialColor = x['materialColor']
        self.ambientColor = x['ambientColor']
        self.colorLightControl.parse_json(x['colorLightControl'])
        self.alphaLightControl.parse_json(x['alphaLightControl'])

    def __str__(self):
        return 'Mat:{} Amb:{}\n\tColorControl: {}\n\tAlphaControl: {}'.format(
                                                                               self.materialColor,
                                                                               self.ambientColor,
                                                                               self.colorLightControl,
                                                                               self.alphaLightControl)

    def enable_vertex_color(self, enabled=True):
        result = False
        if self.colorLightControl.enable_vertex_color(enabled):
            result = True
        if self.alphaLightControl.enable_vertex_color(enabled):
            result = True
        return result

    def is_vertex_color_enabled(self):
        return self.colorLightControl.is_vertex_color_enabled() and \
            self.alphaLightControl.is_vertex_color_enabled()

    def __getitem__(self, item):
        is_color = True if "color" in item else False
        if "control" in item:
            return self.colorLightControl[item] if is_color else self.alphaLightControl[item]
        elif 'enable' in item:
            if "material" in item:
                return self.materialColorEnabled if is_color else self.materialAlphaEnabled
            elif "ambient" in item:
                return self.ambientColorEnabled if is_color else self.ambientAlphaEnabled
            elif "raster" in item:
                return self.rasterColorEnabled if is_color else self.rasterAlphaEnabled
        else:
            if 'material' in item:
                return self.materialColor
            elif 'ambient' in item:
                return self.ambientColor
        raise ValueError(self.LC_ERROR.format(item))

    def __setitem__(self, key, value):
        is_color = True if "color" in key else False
        if "control" in key:
            key2, value = splitKeyVal(value)
            if not key2:
                raise ValueError(self.LC_ERROR.format(key))
            if is_color:
                self.colorLightControl[key2] = value
            else:
                self.alphaLightControl[key2] = value
        elif 'enable' in key:
            val = validBool(value)
            if "material" in key:
                if is_color:
                    self.materialColorEnabled = val
                else:
                    self.materialAlphaEnabled = val
            elif "ambient" in key:
                if is_color:
                    self.ambientColorEnabled = val
                else:
                    self.ambientAlphaEnabled = val
            elif "raster" in key:
                if is_color:
                    self.rasterColorEnabled = val
                else:
                    self.rasterAlphaEnabled = val
        else:
            int_vals = parse_color(value)
            if not int_vals:
                raise ValueError(self.LC_ERROR.format(key))
            if "material" in key:
                self.materialColor = int_vals
            elif "ambient" in key:
                self.ambientColor = int_vals
            else:
                raise ValueError(self.LC_ERROR.format(key))

    class LightChannelControl:
        LIGHT_SOURCE = ("register", "vertex")
        DIFFUSE_FUNCTION = ("disabled", "enabled", "clamped")
        ATTENUATION = ("specular", "spotlight")

        #   Channel control
        #         //0000 0000 0000 0000 0000 0000 0000 0001   Material Source (GXColorSrc)
        #         //0000 0000 0000 0000 0000 0000 0000 0010   Light Enabled
        #         //0000 0000 0000 0000 0000 0000 0011 1100   Light 0123
        #         //0000 0000 0000 0000 0000 0000 0100 0000   Ambient Source (GXColorSrc)
        #         //0000 0000 0000 0000 0000 0001 1000 0000   Diffuse Func
        #         //0000 0000 0000 0000 0000 0010 0000 0000   Attenuation Enable
        #         //0000 0000 0000 0000 0000 0100 0000 0000   Attenuation Function (0 = Specular)
        #         //0000 0000 0000 0000 0111 1000 0000 0000   Light 4567

        def __init__(self, flags):
            self.materialSourceVertex = flags & 1
            self.enabled = flags >> 1 & 1
            self.light0123 = flags >> 2 & 0xf
            self.ambientSourceVertex = flags >> 6 & 1
            self.diffuseFunction = flags >> 7 & 3
            self.attenuationEnabled = flags >> 9 & 1
            self.attenuationFunction = flags >> 10 & 1
            self.light4567 = flags >> 11 & 0xf

        def __eq__(self, other):
            """
            :type other: LightChannel.LightChannelControl
            :return: True if equal
            """
            return self.materialSourceVertex == other.materialSourceVertex and \
                self.enabled == other.enabled and \
                self.light0123 == other.light0123 and \
                self.ambientSourceVertex == other.ambientSourceVertex and \
                self.diffuseFunction == other.diffuseFunction and \
                self.attenuationEnabled == other.attenuationEnabled and \
                self.attenuationFunction == other.attenuationFunction and \
                self.light4567 == other.light4567

        def parse_json(self, json):
            for x in json:
                self[x] = json[x]

        def to_json(self):
            return {
                'materialSourceVertex': self['material'],
                'enabled': str(self['enable']),
                'ambient': self['ambient'],
                'diffuse': self['diffuse'],
                'attenuation': self['attenuation']
            }

        def is_vertex_color_enabled(self):
            return self.materialSourceVertex

        def enable_vertex_color(self, enable):
            if self.materialSourceVertex != enable:
                self.materialSourceVertex = enable
                return True
            return False

        def __str__(self):
            return 'enabled:{} material:{} ambient:{} diffuse:{} attenuation:{}'.format(self['enable'],
                                                                                        self['material'],
                                                                                        self['ambient'],
                                                                                        self['diffuse'],
                                                                                        self['attenuation'])

        def __getitem__(self, item):
            if 'material' in item:
                return self.LIGHT_SOURCE[self.materialSourceVertex]
            elif 'enable' in item:
                return self.enabled
            elif 'ambient' in item:
                return self.LIGHT_SOURCE[self.ambientSourceVertex]
            elif 'diffuse' in item:
                return self.DIFFUSE_FUNCTION[self.diffuseFunction]
            elif 'attenuation' in item:
                return 'None' if not self.attenuationEnabled else self.ATTENUATION[self.attenuationFunction]
            else:
                raise ValueError(LightChannel.LC_ERROR.format(item))

        def __setitem__(self, key, value):
            if 'material' in key:
                i = indexListItem(self.LIGHT_SOURCE, value, self.materialSourceVertex)
                if i >= 0:
                    self.materialSourceVertex = i
            elif 'enable' in key:
                val = validBool(value)
                self.enabled = val
            elif 'ambient' in key:
                i = indexListItem(self.LIGHT_SOURCE, value, self.ambientSourceVertex)
                if i >= 0:
                    self.ambientSourceVertex = i
            elif 'diffuse' in key:
                i = indexListItem(self.DIFFUSE_FUNCTION, value, self.diffuseFunction)
                if i >= 0:
                    self.diffuseFunction = i
            elif 'attenuation' in key:
                try:
                    i = indexListItem(self.ATTENUATION, value, self.attenuationFunction)
                    if i >= 0:
                        self.attenuationFunction = i
                    if not self.attenuationEnabled:
                        self.attenuationEnabled = True
                except ValueError:
                    val = validBool(value)
                    self.attenuationEnabled = val
            else:
                raise ValueError(LightChannel.LC_ERROR.format(key))
