# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImpactRasterCreator
                                 A QGIS plugin
 This plugin generates flood impact maps
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-07-11
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Anthony Cooper
        email                : anthony.cooper@outlook.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
import gdal


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .impact_raster_creator_dialog import ImpactRasterCreatorDialog
import os.path


class ImpactRasterCreator:

    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ImpactRasterCreator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Impact Raster Creator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ImpactRasterCreator', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/impact_raster_creator/impact_raster_creator_icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Impact Raster Creator'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Impact Raster Creator'),
                action)
            self.iface.removeToolBarIcon(action)


    joinedLayers = []
    impactLayers = []
    levelLayers = []
    baseLoc = ''
    calcType = '_dh'
    searchType = 'h_Max'

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = ImpactRasterCreatorDialog()
            self.dlg.pushButton.clicked.connect(self.select_output_folder)

        #Disconnect any update connections whilst initialize
        try: self.dlg.comboBox.currentIndexChanged.disconnect()
        except Exception: pass

        #Set up the type selector
        self.dlg.comboBox_2.clear()
        self.dlg.comboBox_2.addItem('Level')
        self.dlg.comboBox_2.addItem('Depth')
        self.dlg.comboBox_2.addItem('Hazard')
        self.dlg.comboBox_2.addItem('Ground')
        self.dlg.comboBox_2.setCurrentIndex(0)
        self.setType()

        #If no base layer has been selected, pick the first
        if self.dlg.comboBox.currentIndex() == -1:
            self.dlg.comboBox.setCurrentIndex(0)
        #Set default to generate _dh
        self.calcType = '_dh'

        #Update the UI and lists
        self.update()

        #Connect the update to changes in the changing items
        self.dlg.comboBox.currentIndexChanged.connect(self.update)
        self.dlg.comboBox_2.currentIndexChanged.connect(self.setType)
        self.dlg.treeWidget.itemSelectionChanged.connect(self.update)
        self.dlg.lineEdit.textEdited.connect(self.update)

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            folder = self.dlg.outputFolderDlg.text() #set output folder based off current writing
            if not os.path.exists(folder):              #check if the output folder exists
                os.makedirs(folder)                     #create it if not

            #Main Running

            for joinedLayer in self.joinedLayers:                       #For every layer that has been joined
                if joinedLayer[6].isSelected() is True:                                 #If it is selected in UI
                    joinedLayer[5] = os.path.join(folder, joinedLayer[4] + '.tif')      #Set final output file name

                    if joinedLayer[3] is False:                                             #If it already exists in the project
                        QgsProject.instance().removeMapLayer(joinedLayer[7].layerId())      #Unload the layer from the project

                    #Set the calculation type
                    if joinedLayer[8] == '_dh_dx' or joinedLayer[8] == '_dd_dx':
                        calcDo = '((A@1 = -999) AND (B@1 = -999)) * (-999) + ' + \
                        '((A@1 = -999) AND (B@1 != -999)) * -99 + ' + \
                        '((A@1 != -999) AND (B@1 = -999)) * 99 + ' + \
                        '((A@1 != -999) AND (B@1 != -999)) * (A@1 - B@1)'
                    elif joinedLayer[8] == '_dx':
                        calcDo = '((A@1 = -999) AND (B@1 = -999)) * (-999) + ' + \
                        '((A@1 = -999) AND (B@1 != -999)) * -99 + ' + \
                        '((A@1 != -999) AND (B@1 = -999)) * 99 + ' + \
                        '((A@1 != -999) AND (B@1 != -999)) * (-999)'
                    elif joinedLayer[8] == '_dd0' or joinedLayer[8] == '_dZUK':
                        calcDo = '((A@1 = -999) AND (B@1 = -999)) * (-999) + ' + \
                        '((A@1 = -999) AND (B@1 != -999)) * (B@1) + ' + \
                        '((A@1 != -999) AND (B@1 = -999)) * (A@1) + ' + \
                        '((A@1 != -999) AND (B@1 != -999)) * (A@1 - B@1)'
                    elif joinedLayer[8] == '_dh' or joinedLayer[8] == '_dd'or joinedLayer[8] == '_dDEMZ':
                        calcDo = '((A@1 = -999) AND (B@1 = -999)) * (-999) + ' + \
                        '((A@1 = -999) AND (B@1 != -999)) * (-999) + ' + \
                        '((A@1 != -999) AND (B@1 = -999)) * (-999) + ' + \
                        '((A@1 != -999) AND (B@1 != -999)) * (A@1 - B@1)'
                    else:
                        calcDo = '-999'

                    #Pass inputs over to task manager and initialise task
                    globals()['task_' + joinedLayer[4]] = ImpactRasterCalcTask(joinedLayer[4], calcDo, joinedLayer, self.iface)
                    #Start task running
                    QgsApplication.taskManager().addTask(globals()['task_' + joinedLayer[4]])




    def update(self):
        #Set file location
        if self.baseLoc != '':
            self.dlg.outputFolderDlg.setText(self.baseLoc)

        #Load all calc types
        calcTypes = []
        for item in self.dlg.treeWidget.selectedItems():
            calcTypes.append(item.text(1))

        self.joinedLayers = [] #Clear list of joined layers

        AEPs = (self.dlg.lineEdit.text()).split(",") #Create list of events from given string
        ccUps = (self.dlg.lineEdit_2.text()).split(",") #Create list of climate change uplifts

        events =[]
        for AEP in AEPs:
            for ccUp in ccUps:
                events.append('['+AEP+'_CC'+ccUp+']')
        #print(events)

        self.dlg.rasterList.clear() #Clear list of rasters in UI

        baseLayer = 'XYZ'
        for event in events: #For each event
            if len(event)>0: #Check an event has been added
                #print(event)
                eloc = -1
                if self.dlg.comboBox.currentIndex() >= 0 and self.dlg.comboBox.currentIndex() < len(self.levelLayers):
                    eloc = self.levelLayers[self.dlg.comboBox.currentIndex()].name().find(event)    #try to find the event in the layer name, set it to eloc
                    #print(self.levelLayers[self.dlg.comboBox.currentIndex()].name())
                if eloc != -1:      #Once the event has been found (hence eloc != -1)
                    baseLayer = (self.levelLayers[self.dlg.comboBox.currentIndex()].name()).replace(event,'~event~') #sub ~event~ in place of the actual event in the layer name
                    break   #Stop trying to find other events in the layer
        #print(baseLayer)


        baseLayers = [] #blank the list of base layers
        devLayers = []  #blank the list of developed layers

        if baseLayer != 'XYZ': #Check that baselayer has been processed with event
            for levelLayer in self.levelLayers: #for all the water level layers
                for event in events:            #check for each event
                    eloc = levelLayer.name().find(event) #can the event name be found
                    if eloc != -1:  #if event can be found
                        genLayer = (levelLayer.name()).replace(event,'~event~') #sub ~event~ in place of the actual event in the layer name
                        if genLayer == baseLayer: # if this layer has the same name as the baselayer its a baselayer, so store it with its event
                            baseLayers.append([levelLayer, event])
                        else:                     # else its a developed layer so store it with that
                            devLayers.append([levelLayer, event])
                        break
        #print(baseLayers)
        #print(devLayers)
        #Joined developed and base layers together
        for devLayer in devLayers:  #For every developed layer
            for baseLayer in baseLayers: #check every baselayer
                if devLayer[1] == baseLayer[1]: #If it finds a baselayer with same event, add it to the list of joined layers and stop looking
                    for calcType in calcTypes:
                        self.joinedLayers.append([devLayer[0], baseLayer[0], devLayer[1], True, '', '',QListWidgetItem(),'',calcType])
                    break

        #Process the joined layers to develop names and attributes, then add them to the list of layers
        for joinedLayer in self.joinedLayers:
            strSuf = ''
            strPre = ''
            strDev = ''
            strBas = ''
            strEnd = len(self.searchType)+1


            for idx, let in enumerate(joinedLayer[0].name()):
                if let == joinedLayer[1].name()[idx]:
                    strPre = strPre + let
                else:
                    strDev = joinedLayer[0].name()[(idx-len(joinedLayer[0].name())):]
                    strBas = joinedLayer[1].name()[(idx-len(joinedLayer[1].name())):]
                    #print(strDev)
                    #print(strBas)
                    break

            for idx, let in enumerate(reversed(strDev)):
                if let == strBas[len(strBas)-idx-1]:
                    strSuf = let + strSuf
                else:
                    strDev = strDev[:(len(strDev)-strEnd-1)]
                    strBas = strBas[:(len(strBas)-strEnd-1)]
                    #print(strDev)
                    #print(strBas)
                    break

            joinedLayer[4] = strPre + strDev + ']-[' + strBas + ']' + joinedLayer[8]

            for impactLayer in self.impactLayers:
                if joinedLayer[4] == impactLayer.name():
                    joinedLayer[3] = False
                    joinedLayer[7] = impactLayer
                    break

            joinedLayer[6] = QListWidgetItem(joinedLayer[4], self.dlg.rasterList)
            joinedLayer[6].setSelected(joinedLayer[3])

    def setUp(self):
        # Initialise list of level layers
        self.impactLayers = []
        self.levelLayers = []
        layers = []

        # Fetch the currently loaded layers
        layers = self.load_all_layers(QgsProject.instance().layerTreeRoot().children(), layers)

        # Clear the contents of the comboBox from previous runs
        self.dlg.comboBox.clear()

        self.dlg.comboBox.setCurrentIndex(0)
        #print(layers)
        for layer in layers:
            #print(layer.layer())
            if layer.layer() is not None:
                if layer.layer().type() == 1:                   #If they are rasters continue checking
                    if (layer.name()).find(self.searchType) != -1:      #If the are h_max's
                        self.dlg.comboBox.addItem(layer.name()) #Add to the comboBox
                        self.levelLayers.append(layer)          #Add to the list of level layers
                        if (layer.name()).find('BAS') != -1:      #If the layer has BAS anywhere in it - tries to identify base layers
                            self.dlg.comboBox.setCurrentIndex(self.dlg.comboBox.count()-1)  #If it is a base layer select it, then set baseLoc to it, up 3 levels, then Impact folder
                            self.baseLoc = os.path.abspath(os.path.join(os.path.dirname(layer.layer().source()), os.path.pardir, os.path.pardir, os.path.pardir, 'Impact'))
                    elif (layer.name()).find('_dh') != -1 or (layer.name()).find('_dd') != -1 or (layer.name()).find('_dx') != -1 or (layer.name()).find('_dZUK') != -1 or (layer.name()).find('_dDEM') != -1:  #If are _dh, _dx or _dh_dx
                        self.impactLayers.append(layer)         #Add to the list of impact layers

    def setType(self):
        if self.dlg.comboBox_2.currentIndex() == 0:
            self.searchType = 'h_Max'
            self.dlg.treeWidget.clear()
            QTreeWidgetItem(self.dlg.treeWidget,['Impact','_dh'])
            QTreeWidgetItem(self.dlg.treeWidget,['Change in Extents','_dx'])
            QTreeWidgetItem(self.dlg.treeWidget,['Impact and Change in Extents','_dh_dx'])
        elif self.dlg.comboBox_2.currentIndex() == 1:
            self.searchType = 'd_Max'
            self.dlg.treeWidget.clear()
            QTreeWidgetItem(self.dlg.treeWidget,['Impact','_dd'])
            QTreeWidgetItem(self.dlg.treeWidget,['Impact, including from no flooding','_dd0'])
            QTreeWidgetItem(self.dlg.treeWidget,['Change in Extents','_dx'])
            QTreeWidgetItem(self.dlg.treeWidget,['Impact and Change in Extents','_dd_dx'])
        elif self.dlg.comboBox_2.currentIndex() == 2:
            self.searchType = 'ZUK1_Max'
            self.dlg.treeWidget.clear()
            QTreeWidgetItem(self.dlg.treeWidget,['Change in Hazard','_dZUK'])
        elif self.dlg.comboBox_2.currentIndex() == 3:
            self.searchType = 'DEM_Z'
            self.dlg.treeWidget.clear()
            QTreeWidgetItem(self.dlg.treeWidget,['Difference','_dDEMZ'])
        else:
            self.searchType = 'XYZ'
            self.dlg.treeWidget.clear()






        self.setUp()
        self.update()




    def load_all_layers(self, group, layers):
        for child in group:
            if isinstance(child, QgsLayerTreeLayer):
                layers.append(child)
            elif isinstance(child, QgsLayerTreeGroup):
                layers = self.load_all_layers(child.children(), layers)
        return layers



    def select_output_folder(self):
        folder = self.dlg.outputFolderDlg.text()
        folder = self.find_existing(folder)
        folder = QFileDialog.getExistingDirectory(self.dlg, "Open Directory", folder, QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if folder is not '':
            self.dlg.outputFolderDlg.setText(folder)

    def find_existing(self, folder):
        if not os.path.exists(folder):
            folder = os.path.abspath(os.path.join(folder, os.pardir))
            self.find_existing(folder)

        return folder

MESSAGE_CATEGORY = 'ImpactRasterCalcTask'

class ImpactRasterCalcTask(QgsTask):
    """This shows how to subclass QgsTask"""
    def __init__(self, description, calcDo, joinedLayer, iface):
        super().__init__(description, QgsTask.CanCancel)
        self.description = description
        self.calcDo = calcDo
        self.joinedLayer = joinedLayer
        self.total = 0
        self.iterations = 0
        self.exception = None
        self.iface = iface

        #Set up feedback return from raster calculator - feedback is updated from raster calculator between 5% and 95%
        self.feedback = QgsFeedback()
        self.feedback.progressChanged.connect(lambda: self.setProgress(5 + 0.9 * self.feedback.progress()))

    def run(self):
        """Here you implement your heavy lifting.
        Should periodically test for isCanceled() to gracefully
        abort.
        This method MUST return True or False.
        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished
        """
        QgsMessageLog.logMessage('Started task "{}"'.format(
                                     self.description),
                                 MESSAGE_CATEGORY, Qgis.Info)

        #Load new copies of input layers
        layerA = QgsRasterLayer(self.joinedLayer[0].layer().source(), self.joinedLayer[4] + '_' + self.joinedLayer[0].layer().name())
        layerB = QgsRasterLayer(self.joinedLayer[1].layer().source(), self.joinedLayer[4] + '_' + self.joinedLayer[1].layer().name())

        #Set new input layers to not use no data values (all pixels are calculated on)
        layerA.dataProvider().setUseSourceNoDataValue(1,False)
        layerB.dataProvider().setUseSourceNoDataValue(1,False)

        #Define the items being added to the raster calculator; A is new layer, B is baseline
        entries = []
        A = QgsRasterCalculatorEntry()
        A.ref = 'A@1'
        A.raster = layerA
        A.bandNumber = 1
        entries.append(A)
        B = QgsRasterCalculatorEntry()
        B.ref = 'B@1'
        B.raster = layerB
        B.bandNumber = 1
        entries.append(B)

        self.setProgress(5) #Set progress to 5% to reflect loading in of layers

        #Do the calculation and create a temp output
        calc = QgsRasterCalculator(self.calcDo, '/vsimem/'+self.joinedLayer[4]+'.tif', 'GTiff', self.joinedLayer[0].layer().extent(), self.joinedLayer[0].layer().width(), self.joinedLayer[0].layer().height(), entries)
        calcRes = calc.processCalculation(self.feedback)

        self.setProgress(95)

        if calcRes == 0: #If the calculation worked
            #Process the temp output to remove nodata values
            gdal.Translate(self.joinedLayer[5], gdal.Open('/vsimem/'+self.joinedLayer[4]+'.tif'), options=gdal.TranslateOptions(noData=-999, outputSRS=QgsProject.instance().crs().authid()))
        else:
            self.exception = calcRes
            return False

        # check isCanceled() to handle cancellation
        if self.isCanceled():
            return False
        return True

    def finished(self, result):
        """
        This function is automatically called when the task has
        completed (successfully or not).
        You implement finished() to do whatever follow-up stuff
        should happen after the task is complete.
        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.
        result is the return value from self.run.
        """

        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed\n'.format(name=self.description),
              MESSAGE_CATEGORY, Qgis.Success)

            #Add layer to interface
            newLayer = self.iface.addRasterLayer(self.joinedLayer[5],self.joinedLayer[4])

        else:
            if self.exception is None:
                self.feedback.cancel()
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description),
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage('Task "{name}" Exception: {exception}'.format(name=self.description,exception=self.exception),MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception

    def cancel(self):
        self.feedback.cancel()

        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
