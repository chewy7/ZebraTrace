#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#	Copyright 2012 Maxim.S.Barabash <maxim.s.barabash@gmail.com>
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import shutil
import time

from PyQt4 import QtCore, QtGui
from .gui.widgets.svgview import *
from .gui.ui_mainwindow import Ui_MainWindow

from .geom.funcplotter2 import FuncPlotter
from .geom.function import Function
from .app_config import Preset
from .utils import unicode
from .utils import xrange



# FIXME move to class Info to funcplotter2
class Info(QtCore.QObject):
	def __init__(self):
		QtCore.QObject.__init__(self)
		self.clear()

	def clear(self):
		self.traceTime = 0.0
		self.numberObject = 0
		self.numberNodes = 0

	def __setattr__(self, attr, value):
		if not hasattr(self, attr) or getattr(self, attr) != value:
			self.__dict__[attr] = value
			self.emit(QtCore.SIGNAL("infoChanget()"))

	def __call__(self):
		text = ''
		text += unicode(self.tr("Time trace: %5.3f seconds.\n")) % self.traceTime
		text += unicode(self.tr("Graphic Objects\n  Number of objects: %i\n  Number of nodes: %i\n")) % (self.numberObject, self.numberNodes)
		return text


class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
	def __init__(self, data, config):
		QtGui.QMainWindow.__init__(self)
		self.setupUi(self)
		self.trace_image = ""
		self.app_data = data
		self.config = config
		self.info = Info()

		self.image_size = [1000, 1000]
		self.dimensions = [-1, -1, 1, 1]

		self.Escape = False

		self.view = TraceCanvas()
		self.createActions()

		self.tabPreferences.setCurrentIndex(0)
		self.topPanel.setEnabled(False)
		self.buttonTrace.setEnabled(False)
		self.buttonSave.setEnabled(False)
		self.actionSaveAs.setEnabled(False)
		self.sliderTransparency.setEnabled(False)
		self.viewContainer.addWidget(self.view)
		self.loadConfig(self.app_data.app_config)
		self.setWindowTitle("%s" % self.app_data.app_name)

	def __del__(self):
		import os
		self.saveConfig(self.app_data.app_config)
		if os.path.isfile(self.app_data.temp_svg):
			os.remove(self.app_data.temp_svg)

	def keyPressEvent(self, event):
		if type(event) == QtGui.QKeyEvent:
			if (event.key() == QtCore.Qt.Key_Escape):
				self.Escape = True
			event.accept()
		else:
			event.ignore()

	def createActions(self):
		self.actionOpenBitmap.triggered.connect(self.openFileBitmap)
		self.actionSaveAs.triggered.connect(self.saveFileAs)
		self.actionSavePreset.triggered.connect(self.savePreset)
		self.actionLoadPreset.triggered.connect(self.loadPreset)
		self.actionQuit.triggered.connect(QtGui.qApp.quit)
		self.actionAbout.triggered.connect(self.about)
		self.actionAboutQt.triggered.connect(QtGui.qApp.aboutQt)
		self.connect(self.buttonTrace,
					QtCore.SIGNAL("clicked()"), self.trace)
		self.connect(self.buttonSave,
					QtCore.SIGNAL("clicked()"), self.saveFileAs)
		self.connect(self.buttonHelp,
					QtCore.SIGNAL("clicked()"), self.help)

		self.connect(self,
					QtCore.SIGNAL("loadPreset()"), self.trace)
#		self.connect(self,
#					QtCore.SIGNAL("openFileBitmap()"), self.trace)
		self.connect(self.info,
					QtCore.SIGNAL("infoChanget()"), self.infoUpdate)

		self.actionBackground.toggled.connect(self.view.setViewBackground)
		self.actionBorder.toggled.connect(self.view.setViewOutline)
		self.sliderTransparency.valueChanged.connect(self.view.setOpacity)
		self.previewMode.currentIndexChanged.connect(self.sliderTransparency.setEnabled)
		self.previewMode.currentIndexChanged.connect(self.view.setViewTraceImage)
		self.previewMode.currentIndexChanged.connect(self.labelTransparency.setEnabled)
		self.info.clear()

	def openFileBitmap(self, path=None):
		if not path:
			path = QtGui.QFileDialog.getOpenFileName(self, self.tr("Open Bitmap File"),
				unicode(self.config.currentPath),
				self.tr("Bitmap files (*.jpg *.ipeg *.png *.gif *.tiff);;All files (*.*)"))
		if path:
			self.trace_image = unicode(path)
			self.config.currentPath = unicode(os.path.dirname(self.trace_image))
			img = QtGui.QImage(self.trace_image)
			img_w = float(img.width())
			img_h = float(img.height())
			img_d = [[1, img_w / img_h], [img_h / img_w, 1]][img_w > img_h]
			self.image_size = [img_w, img_h]
			self.dimensions = [-1 * img_d[1], -1 * img_d[0], 1 * img_d[1], 1 * img_d[0]]
			self.view.openFileIMG(path)
			self.view.resetTransform()
			self.topPanel.setEnabled(True)
			self.setWindowTitle("%s - %s" % (self.app_data.app_name, os.path.basename(self.trace_image)))
			self.previewMode.setCurrentIndex(1)
			self.buttonTrace.setEnabled(True)
			self.buttonSave.setEnabled(False)
			self.actionSaveAs.setEnabled(False)
			self.emit(QtCore.SIGNAL("openFileBitmap()"))

	def saveFileAs(self, path=None):
		if not path:
			path = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save File"),
				unicode(self.config.currentPath), self.tr("SVG files (*.svg)"))
		if path:
			svg_file = unicode(path)
			self.config.currentPath = unicode(os.path.dirname(svg_file))
			shutil.copy(self.app_data.temp_svg, svg_file)

	def loadPreset(self, path=None):
		if not path:
			path = QtGui.QFileDialog.getOpenFileName(self, self.tr("Load Preset File"),
				unicode(self.config.presetPath), self.tr("Preset files (*.preset)"))
		if path:
			preset_file = unicode(path)
			self.config.presetPath = unicode(os.path.dirname(preset_file))
			preset = Preset()
			preset.load(preset_file)
			self.lineEditX.setText(unicode(preset.funcX))
			self.lineEditY.setText(unicode(preset.funcY))
			self.rangeMin.setValue(preset.rangeMin)
			self.rangeMax.setValue(preset.rangeMax)
			self.emit(QtCore.SIGNAL("loadPreset()"))

	def savePreset(self, path=None):
		if not path:
			path = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save Preset File"),
				unicode(self.config.presetPath), self.tr("Preset files (*.preset)"))
		if path:
			preset_file = unicode(path)
			self.config.presetPath = unicode(os.path.dirname(preset_file))
			preset = Preset()
			preset.funcX = unicode(self.lineEditX.text())
			preset.funcY = unicode(self.lineEditY.text())
			preset.rangeMin = self.rangeMin.value()
			preset.rangeMax = self.rangeMax.value()
			preset.save(preset_file)

	def loadConfig(self, path=None):
		self.config.load(path)
		config = self.config
		self.numberCurves.setValue(config.numberCurves)
		self.curveResolution.setValue(config.curveResolution)
		self.curveWidthMin.setValue(config.curveWidthMin)
		self.curveWidthMax.setValue(config.curveWidthMax)
		self.nodeReduction.setValue(config.nodeReduction)

		self.lineEditX.setText(unicode(config.funcX))
		self.lineEditY.setText(unicode(config.funcY))
		self.rangeMin.setValue(config.rangeMin)
		self.rangeMax.setValue(config.rangeMax)
		self.sliderTransparency.setValue(config.sliderTransparency)

	def configUpdate(self, cnf=None):
		if cnf == None:
			cnf = {"numberCurves": self.numberCurves.value(),
			"curveResolution": self.curveResolution.value(),
			"curveWidthMin": self.curveWidthMin.value(),
			"curveWidthMax": self.curveWidthMax.value(),
			"nodeReduction": self.nodeReduction.value(),
			"funcX": unicode(self.lineEditX.text()),
			"funcY":  unicode(self.lineEditY.text()),
			"rangeMin": self.rangeMin.value(),
			"rangeMax": self.rangeMax.value(),
			"sliderTransparency": self.sliderTransparency.value()
			}
		self.config.update(cnf)

	def saveConfig(self, path=None):
		if path is None:
			path = self.app_data.app_config
		self.configUpdate()
		self.config.save(path)

	def help(self):
		import webbrowser
		url = self.app_data.help_index
		webbrowser.open(url)

	def infoUpdate(self):
		self.infoText.setPlainText(self.info())

	def about(self):
		about = unicode(self.tr("""<center><b>%s</b> version %s. <br><br>
See <a href="http://linuxgraphics.ru/">linuxgraphics.ru</a>
for more information.<br><br>
Copyright (C) 2012</center>"""))
		QtGui.QMessageBox.about(self, self.tr("About"), about % (self.app_data.app_name,
														self.app_data.app_version))

	def trace(self):
		if not(self.buttonTrace.isEnabled()):
			return
		self.info.clear()
		self.saveConfig()
		self.buttonTrace.setEnabled(False)
		self.buttonSave.setEnabled(False)
		self.actionSaveAs.setEnabled(False)
		self.Escape = False
		config = self.config
		image_size = self.image_size
		dimensions = self.dimensions
		n = config.numberCurves							# number of curves
		alpha = [config.rangeMin, config.rangeMax]		# range of the variable
		resolution = config.curveResolution				# curve quality
		stroke_color = "none"							# no stroke (when tracing is used fill)
		width_range = [config.curveWidthMin, config.curveWidthMax]
		tolerance = config.nodeReduction / 100.
		funcX = Function(config.funcX)
		funcY = Function(config.funcY)

		fp = FuncPlotter(image_size, dimensions, trace_image=self.trace_image,
						width_range=width_range)

		self.progressBar.setMaximum(n + 1)
		start = time.time()

		for i in xrange(1, n + 1):
			if not(self.Escape):
				fX = funcX({'i': float(i), 'n': n})
				fY = funcY({'i': float(i), 'n': n})
				auto_resolution = fp.auto_resolution(fX, fY, alpha)
				fp.append_func(fX,
								fY,
								alpha,
								(resolution + auto_resolution) * 0.5,
								stroke_color,
								close_path=True,
								tolerance=tolerance)
				self.info.numberNodes += len(fp.coords) - 1
				self.info.numberObject += 1
				self.info.traceTime = time.time() - start

				QtGui.QApplication.processEvents()
				self.progressBar.setValue(i)
			else:
				break

		fp.plot(self.app_data.temp_svg)

		self.info.traceTime = time.time() - start

		self.view.openFileSVG(QtCore.QFile(self.app_data.temp_svg))
		self.progressBar.setValue(0)
		self.buttonTrace.setEnabled(True)
		self.buttonTrace.setFocus(True)
		self.buttonSave.setEnabled(True)
		self.actionSaveAs.setEnabled(True)