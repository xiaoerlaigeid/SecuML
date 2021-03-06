## SecuML
## Copyright (C) 2016  ANSSI
##
## SecuML is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## SecuML is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with SecuML. If not, see <http://www.gnu.org/licenses/>.

from SecuML.Plots.HexagonalBinning import HexagonalBinning

class Visualization(object):

    def __init__(self, projection, experiment):
        self.projection = projection
        self.experiment = experiment

    def allHexBin(self, projected_instances):
        malicious_ids = projected_instances.getMaliciousIds()
        num_components = projected_instances.numFeatures()
        num_components = min(num_components, 10)
        for i in range(num_components - 1):
            for j in range(i+1, num_components):
                self.oneHexBin(projected_instances, i, j, malicious_ids)

    ## Algorithm from 'Scatterplot matrix techniques for large N'
    ## by Carr, Littlefield, Nicholson, and Littlefield
    def oneHexBin(self, projected_instances, cx_index, cy_index,
                  malicious_ids):
        x = projected_instances.getFeatureValuesFromIndex(cx_index)
        y = projected_instances.getFeatureValuesFromIndex(cy_index)
        hex_bin = HexagonalBinning(x, y,
                projected_instances.getIds(), 30, malicious_ids)
        hex_bin.computeBinning()
        output_file  = self.experiment.getOutputDirectory()
        output_file += 'c_'+ str(cx_index) + '_' + str(cy_index) + '_hexbin'
        output_file += '.json'
        hex_bin.printBinning(cx_index, cy_index, output_file)
