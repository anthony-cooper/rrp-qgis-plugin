import random
from time import sleep

from qgis.core import *

MESSAGE_CATEGORY = 'ImpactRasterCalcTask'

class ImpactRasterCalcTask(QgsTask):
    """This shows how to subclass QgsTask"""
    def __init__(self, description, duration):
        super().__init__(description, QgsTask.CanCancel)
        self.description = description
        self.calcDo = calcDo
        self.joinedLayer = joinedLayer
        self.entries = entries

        self.total = 0
        self.iterations = 0
        self.exception = None
    def run(self):
        """Here you implement your heavy lifting.
        Should periodically test for isCanceled() to gracefully
        abort.
        This method MUST return True or False.
        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished
        """
        QgsMessageLog.logMessage('Started task "{}"'.format(
                                     self.description()),
                                 MESSAGE_CATEGORY, Qgis.Info)

            #Do the calculation and create a temp output
            calc = QgsRasterCalculator(self.calcDo, '/vsimem/in_memory_output.tif', 'GTiff', self.joinedLayer[0].layer().extent(), self.joinedLayer[0].layer().width(), self.joinedLayer[0].layer().height(), self.entries)
            calcRes = calc.processCalculation()

            #Move to finished(/cancelled?)
            #Turn nodata values back on
            self.joinedLayer[0].layer().dataProvider().setUseSourceNoDataValue(1,True)
            self.joinedLayer[1].layer().dataProvider().setUseSourceNoDataValue(1,True)

            if calcRes == 0: #If the calculation worked
                #Process the temp output to remove nodata values
                gdal.Translate(self.joinedLayer[5], gdal.Open('/vsimem/in_memory_output.tif'), options=gdal.TranslateOptions(noData=-999))

                #Move to finished
                #Add layer to interface
                newLayer = self.iface.addRasterLayer(self.joinedLayer[5],self.joinedLayer[4])

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
                'Task "{name}" completed\n' \
                'Total: {total} (with {iterations} '\
              'iterations)'.format(
                  name=self.description(),
                  total=self.total,
                  iterations=self.iterations),
              MESSAGE_CATEGORY, Qgis.Success)
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description()),
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception

    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()

import __main__

longtask = ImpactRasterCalcTask(description, v)

QgsApplication.taskManager().addTask(longtask)
