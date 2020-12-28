import os

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QComboBox, QSlider
from PyQt5.QtWidgets import QWidget, QGridLayout, QScrollArea, QVBoxLayout, QLabel, QHBoxLayout, QTabWidget, QCheckBox, \
    QFrame

from abmatt.brres import Brres
from abmatt.brres.lib.node import ClipableObserver
from abmatt.brres.mdl0.material.material import Material
from abmatt.gui.brres_path import BrresPath, get_material_by_url
from abmatt.gui.color_widget import ColorWidget
from abmatt.gui.map_widget import Tex0WidgetGroup, Tex0WidgetSubscriber
from abmatt.gui.mat_widget import MaterialWidget, MatWidgetHandler
from abmatt.gui.material_editor import MaterialEditor


class MaterialTabs(QWidget, MatWidgetHandler):
    def on_material_edit(self, material):
        mat_editor = MaterialEditor(material)

    def on_material_remove(self, material):
        pass

    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout()
        # Material selection tabs
        tab_widget = QTabWidget(self)
        layout.addWidget(tab_widget)
        self.tabBar = tab_widget.tabBar()
        # self.tabBar.setMouseTracking(True)
        # self.tabBar.installEventFilter(self)
        self.material_library = MaterialLibrary(self, Brres.get_material_library())
        tab_widget.addTab(self.material_library, 'Library Materials')
        self.scene_library = MaterialBrowser(self)
        tab_widget.addTab(self.scene_library, 'Scene Materials')
        self.editor = MaterialSmallEditor(self)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def __init_material_editor(self, layout):
        # Material edit tab
        widget = QWidget()
        layout.addWidget(widget)
        grid = QGridLayout()
        widget.setLayout(grid)
        # Left
        name_label = QLabel('Material:')
        cull_label = QLabel('Cull:')
        trans_label = QLabel('Transparency threshold:')
        color_label = QLabel('Color:')
        self.blend = QCheckBox('Blend')
        maps = QLabel('Maps:')
        grid.addWidget(name_label)
        grid.addWidget(cull_label)
        grid.addWidget(trans_label)
        grid.addWidget(color_label)
        grid.addWidget(self.blend)
        grid.addWidget(maps)
        # Right

    def eventFilter(self, obj, ev):
        if obj == self.tabBar:
            # print(ev.type())
            if ev.type() == QEvent.MouseMove:
                index = self.tabBar.tabAt(ev.pos())
                self.tabBar.setCurrentIndex(index)
                return True
        return super().eventFilter(obj, ev)

    def add_brres_materials_to_scene(self, brres):
        self.scene_library.add_brres_materials(brres)

    def add_materials_to_library(self, materials):
        self.material_library.add_materials(materials)

    def add_material_to_library(self, material):
        self.material_library.add_material(material)

    def on_material_select(self, material):
        """Handles material selection event"""
        self.editor.set_material(material)


class MaterialBrowser(QWidget, MatWidgetHandler):
    def on_material_select(self, material):
        self.handler.on_material_select(material)

    def on_material_edit(self, material):
        self.handler.on_material_edit(material)

    def on_material_remove(self, material):
        self.remove_material(material)
        self.handler.on_material_remove(material)

    def remove_material(self, material):
        b_path = BrresPath(material=material).get_path()
        if b_path in self.materials:
            widget = self.materials.pop(b_path)
            self.grid.removeWidget(widget)

    def __init__(self, parent):
        super().__init__(parent)
        self.handler = parent
        self.is_material_removable = False
        self.init_UI()
        self.grid_col_max = 4
        self.materials = {}

    def init_UI(self):
        # self.group = QGroupBox('Materials', self)
        content = QWidget()
        self.grid = QGridLayout(self)
        self.grid_row = self.grid_col = 0
        content.setLayout(self.grid)
        self.scroll_area = QScrollArea(self)
        # self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(content)
        self.horz_layout = QHBoxLayout()
        self.horz_layout.addWidget(self.scroll_area)
        self.setLayout(self.horz_layout)

    def add_brres_materials(self, brres):
        for model in brres.models:
            for material in model.materials:
                self.add_material(material)

    def increment_grid(self):
        row = self.grid_row
        col = self.grid_col
        if col >= self.grid_col_max - 1:
            self.grid_col = 0
            self.grid_row += 1
        else:
            self.grid_col += 1
        return row, col

    def add_materials(self, materials):
        for x in materials:
            self.add_material(x)

    def add_material(self, material):
        mat_path = BrresPath(material=material)
        name = mat_path.get_path()
        if name not in self.materials:
            label = MaterialWidget(self, self, material, mat_path, self.is_material_removable)
            self.materials[name] = label
            # label.setFixedWidth(120)
            self.grid.addWidget(label, *self.increment_grid())
            return True
        return False


class MaterialLibrary(MaterialBrowser):
    """
    Material Browser that can also add and remove materials and be saved
    """

    def __init__(self, parent, material_library):
        super().__init__(parent)
        self.brres = None
        self.is_material_removable = True
        self.setAcceptDrops(True)
        self.add_materials(material_library.values())
        for x in material_library:
            self.brres = material_library[x].parent.parent
            break

    def can_add_material(self, mat_path):
        return mat_path not in self.materials

    def add_material(self, material):
        if super().add_material(material) and self.brres is not None:
            self.brres.models[0].add_material(material)
            self.brres.save(overwrite=True)

    def remove_material(self, material):
        b_path = BrresPath(material=material).get_path()
        if b_path in self.materials:
            self.brres.models[0].remove_material(material)
            widget = self.materials.pop(b_path)
            self.grid.removeWidget(widget)
            self.brres.save()

    def get_brres_url(self, url):
        path = url.toLocalFile()
        if os.path.splitext(os.path.split(path)[1])[1].lower() == '.brres':
            return path

    def get_brres_urls(self, urls):
        ret = []
        for x in urls:
            b_url = self.get_brres_url(x)
            if not b_url:
                return None
            ret.append(b_url)
        return ret

    def dropEvent(self, a0):
        data = a0.mimeData()
        if data.hasUrls():
            burls = self.get_brres_urls(data.urls())
            if burls:
                for path in burls:
                    self.add_brres_materials(Brres.get_brres(path, True))
                a0.accept()
                return
        elif data.hasText() and self.can_add_material(data.text()):
            mat = get_material_by_url(data.text(), True)
            if mat:
                self.add_material(mat)
                a0.accept()
                return
        a0.ignore()

    def dragEnterEvent(self, a0):
        md = a0.mimeData()
        if (md.hasUrls() and self.get_brres_urls(md.urls())) \
                or (md.hasText() and self.can_add_material(md.text())):
            a0.accept()
        else:
            a0.ignore()

    def dragMoveEvent(self, a0):
        md = a0.mimeData()
        if md.hasUrls() and self.get_brres_urls(md.urls()) \
                or md.hasText() and self.can_add_material(md.text()):
            a0.accept()
        else:
            a0.ignore()


class MaterialSmallEditor(QFrame, ClipableObserver, Tex0WidgetSubscriber):
    def on_map_add(self, tex0, index):
        self.material.addLayer(tex0.name)

    def on_map_remove(self, tex0, index):
        self.material.removeLayerI(index)

    def on_map_replace(self, tex0, index):
        self.material.layers[index].setName(tex0.name)

    def on_map_change(self, tex0, index):
        pass

    def __init__(self, parent, material=None):
        super().__init__(parent)
        self.__init_material_editor()
        if material is not None:
            self.set_material(material)
        else:
            self.material = None

    def __init_material_editor(self):
        # Material edit tab
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setLineWidth(2)
        grid = QGridLayout()
        self.setLayout(grid)
        # Left
        name_label = QLabel('Material:')
        cull_label = QLabel('Cull:')
        trans_label = QLabel('Transparency threshold:')
        color_label = QLabel('Color:')
        self.blend = QCheckBox('Blend')
        self.blend.clicked.connect(self.on_blend_change)
        anims = QLabel('Animations:')
        maps = QLabel('Maps:')
        grid.addWidget(name_label)
        grid.addWidget(cull_label)
        grid.addWidget(trans_label)
        grid.addWidget(color_label)
        grid.addWidget(self.blend)
        grid.addWidget(anims)
        grid.addWidget(maps)
        # Right
        self.name_edit = QLabel()
        # self.name_edit.setReadOnly(True)
        self.cull_combo = cull_combo = QComboBox()
        for cull_option in Material.CULL_STRINGS:
            cull_combo.addItem(cull_option)
        cull_combo.currentIndexChanged.connect(self.on_cull_change)
        self.transparency = QSlider(Qt.Horizontal)
        self.transparency.setMinimum(0)
        self.transparency.setMaximum(255)
        self.transparency.valueChanged.connect(self.on_transparency_change)
        self.colors = ColorGroup()
        self.maps = Tex0WidgetGroup(self)
        self.animations = QLabel('None', self)
        grid.addWidget(self.name_edit, 0, 1)
        grid.addWidget(self.cull_combo, 1, 1)
        grid.addWidget(self.transparency, 2, 1)
        grid.addWidget(self.colors, 3, 1)
        grid.addWidget(self.animations, 5, 1)
        grid.addWidget(self.maps, 6, 1)

    def on_blend_change(self):
        if self.material:
            checked = self.blend.isChecked()
            self.material.enable_blend(checked)

    def on_transparency_change(self):
        if self.material:
            value = self.transparency.value()
            self.material.set_transparency_threshold(value)

    def on_cull_change(self, i):
        if self.material:
            self.material.setCullModeStr(self.cull_combo.currentText())

    def on_node_update(self, material):
        self.name_edit.setText(material.name)
        self.cull_combo.setCurrentText(material.getCullMode())
        trans = material.get_transparency_threshold()
        if trans != self.transparency.value():
            self.transparency.setValue(trans)
        self.blend.setChecked(material.is_blend_enabled())
        # self.colors = ColorGroup(material.get_colors_used())
        self.colors.set_colors(material.get_colors_used())
        self.update_children(material)

    def update_children(self, material):
        self.maps.set_tex0s(material.get_tex0s())
        self.maps.set_brres(material.getBrres())
        if material.srt0:
            anims = 'Srt0'
        elif material.pat0:
            anims = 'Pat0'
        else:
            anims = 'None'
        self.animations.setText(anims)

    def on_child_update(self, child):
        self.update_children(child.parent)

    def set_material(self, material):
        if material is not self.material:
            if self.material:
                self.material.unregister(self)
            self.material = material
            material.register_observer(self)
            self.on_node_update(material)


class ColorGroup(QWidget):
    def __init__(self, colors=None):
        super().__init__()
        self.widgets = []
        self.layout = None
        self.set_colors(colors)

    def set_colors(self, colors):
        if self.layout is None:
            self.layout = QHBoxLayout()
            self.setLayout(self.layout)
        else:
            while len(self.widgets):
                widget = self.widgets.pop(0)
                self.layout.removeWidget(widget)
                widget.deleteLater()
        if colors:
            for x in colors:
                if x == 'vertex':
                    widget = QLabel(x)
                else:
                    widget = ColorWidget(color=x[1], text=x[0])
                self.layout.addWidget(widget)
                self.widgets.append(widget)
            self.setLayout(self.layout)

