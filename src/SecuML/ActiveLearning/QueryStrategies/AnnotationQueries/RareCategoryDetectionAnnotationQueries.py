## SecuML
## Copyright (C) 2016-2017  ANSSI
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

## package for float division (/)
## in order to perform integer division (//)
from __future__ import division
import copy
import numpy as np
import random
import time

from SecuML.Classification.ClassifierDatasets import ClassifierDatasets
from SecuML.Clustering.Configuration.ClusteringConfiguration import ClusteringConfiguration
from SecuML.Clustering.Clustering import Clustering
from SecuML.Experiment.ClassificationExperiment import ClassificationExperiment
from SecuML.Experiment.ClusteringExperiment import ClusteringExperiment
from SecuML.Tools import matrix_tools

from AnnotationQueries import AnnotationQueries
from AnnotationQuery   import AnnotationQuery

from Categories import Categories

class RareCategoryDetectionAnnotationQueries(AnnotationQueries):

    def __init__(self, iteration, label, proba_min, proba_max,
            multiclass_model = None,
            multiclass_exp = None):
        AnnotationQueries.__init__(self, iteration, label)
        self.proba_min = proba_min
        self.proba_max = proba_max
        self.rare_category_detection_conf = self.iteration.experiment.conf.rare_category_detection_conf
        self.multiclass_model = multiclass_model
        self.multiclass_exp = multiclass_exp

    def run(self, already_queried = None):
        self.runModels(already_queried = already_queried)
        start_time = time.time()
        self.generateAnnotationQueries()
        self.generate_queries_time = time.time() - start_time
        self.exportAnnotationQueries()
        self.generateClusteringVisualization()

    def runModels(self, already_queried = None):
        df = matrix_tools.extractRowsWithThresholds(self.predictions,
                self.proba_min, self.proba_max, 'predicted_proba')
        if already_queried is not None:
            self.predicted_ids = list(set(df.index).difference(set(already_queried)))
        else:
            self.predicted_ids = list(df.index)
        datasets = self.iteration.datasets
        self.annotated_instances = datasets.getAnnotatedInstances(label = self.label)
        self.families_analysis   = self.familiesAnalysis()
        if self.families_analysis:
            self.annotations_type = 'families'
            start_time = time.time()
            self.buildCategories()
            self.analysis_time = time.time() - start_time
            self.categories.setLikelihood(self.iteration.iteration_number)
        else:
            self.annotations_type = 'individual'
            self.categories       = None
            self.analysis_time    = 0

    def generateAnnotationQueries(self):
        num_annotations = self.rare_category_detection_conf.num_annotations
        if not self.families_analysis:
            selected_instances = self.predicted_ids
            if len(selected_instances) > num_annotations:
                selected_instances = random.sample(selected_instances, num_annotations)
            self.annotation_queries = []
            for instance_id in selected_instances:
                predicted_proba = self.predictions.loc[instance_id]['predicted_proba']
                query = AnnotationQuery(instance_id, predicted_proba, self.label, None)
                self.annotation_queries.append(query)
        else:
            self.categories.generateAnnotationQueries(self.rare_category_detection_conf)

    def exportAnnotationQueries(self):
        if not self.families_analysis:
            AnnotationQueries.exportAnnotationQueries(self)
        else:
            filename  = self.iteration.output_directory
            filename += 'toannotate_' + self.label + '.json'
            self.categories.exportAnnotationQueries(filename)

    def annotateAuto(self):
        if not self.families_analysis:
            AnnotationQueries.annotateAuto(self)
        else:
            self.categories.annotateAuto(self.iteration)

    def getManualAnnotations(self):
        if not self.families_analysis:
            AnnotationQueries.getManualAnnotations(self)
        else:
            self.categories.getManualAnnotations(self.iteration)

    def checkAnnotationQueriesAnswered(self):
        if not self.families_analysis:
            return AnnotationQueries.checkAnnotationQueriesAnswered(self)
        else:
            return self.categories.checkAnnotationQueriesAnswered(self.iteration)

    #######################
    ### Private methods ###
    #######################

    def createMulticlassExperiment(self):
        conf = self.rare_category_detection_conf.classification_conf
        exp  = self.iteration.experiment
        name = '-'.join(['AL' + str(exp.experiment_id),
                         'Iter' + str(self.iteration.iteration_number),
                         self.label,
                         'analysis'])
        multiclass_exp = ClassificationExperiment(exp.project, exp.dataset, exp.session,
                                                  experiment_name = name,
                                                  labels_id = exp.labels_id,
                                                  parent = exp.experiment_id)
        multiclass_exp.setFeaturesFilenames(exp.features_filenames)
        multiclass_exp.setClassifierConf(conf)
        multiclass_exp.createExperiment()
        multiclass_exp.export()
        return multiclass_exp

    def buildCategories(self):
        multiclass_exp = self.buildMulticlassClassifier()
        train = self.multiclass_model.datasets.train_instances
        test  = self.multiclass_model.datasets.test_instances
        all_instances = copy.deepcopy(test)
        all_instances.union(train)
        if test.numInstances() > 0:
            predicted_families = self.multiclass_model.testing_monitoring.getPredictedLabels()
            all_families       = list(predicted_families) + train.families
            predicted_proba    = self.multiclass_model.testing_monitoring.getAllPredictedProba()
            for family in train.families:
                probas = [int(family == s) for s in self.multiclass_model.class_labels]
                predicted_proba = np.vstack((predicted_proba, np.array(probas)))
        else:
            all_families    = self.annotated_instances.families
            predicted_proba = None
            for family in self.annotated_instances.families:
                probas = [int(family == s) for s in self.multiclass_model.class_labels]
                if predicted_proba is None:
                    predicted_proba = np.array(probas)
                else:
                    predicted_proba = np.vstack((predicted_proba, np.array(probas)))
        labels_values = list(self.multiclass_model.class_labels)
        assigned_categories = [labels_values.index(x) for x in all_families]
        self.categories = Categories(multiclass_exp,
                                     all_instances,
                                     assigned_categories,
                                     predicted_proba,
                                     self.label,
                                     self.multiclass_model.class_labels)

    def buildMulticlassClassifier(self):
        if self.multiclass_model is not None:
            return self.multiclass_exp
        multiclass_exp = self.createMulticlassExperiment()
        datasets = self.iteration.datasets
        predicted_instances = datasets.getInstancesFromIds(self.predicted_ids)
        multiclass_datasets = ClassifierDatasets(multiclass_exp.classification_conf)
        multiclass_datasets.train_instances = self.annotated_instances
        multiclass_datasets.test_instances  = predicted_instances
        multiclass_datasets.setSampleWeights()
        self.multiclass_model = multiclass_exp.classification_conf.model_class(
                multiclass_exp.classification_conf,
                multiclass_datasets,
                cv_monitoring = True)
        self.multiclass_model.run(multiclass_exp.getOutputDirectory(),
                                  multiclass_exp)
        return multiclass_exp

    # A multi class supervised model is learned from the annotated instances if:
    #       - there are at most 2 families
    #       - the second most represented family has at least 2 instances
    def familiesAnalysis(self):
        num_families = len(self.annotated_instances.getFamiliesValues())
        if num_families < 2:
            return False
        families_counts = self.annotated_instances.getFamiliesCount()
        families_counts = [(k, x) for k, x in families_counts.iteritems()]
        families_counts.sort(key=lambda tup: tup[1], reverse = True)
        if families_counts[1][1] < 2:
            return False
        return True

    def createClusteringExperiment(self):
        conf = ClusteringConfiguration(self.categories.numCategories())
        exp  = self.iteration.experiment
        name = '-'.join(['AL' + str(exp.experiment_id),
                         'Iter' + str(self.iteration.iteration_number),
                         self.label,
                         'clustering'])
        clustering_exp = ClusteringExperiment(exp.project, exp.dataset, exp.session,
                                              conf,
                                              labels_id = exp.labels_id,
                                              experiment_name = name,
                                              parent = exp.experiment_id)
        clustering_exp.setFeaturesFilenames(exp.features_filenames)
        clustering_exp.createExperiment()
        clustering_exp.export()
        return clustering_exp

    def generateClusteringVisualization(self):
        if self.families_analysis:
            self.clustering_exp = self.createClusteringExperiment()
            clustering = Clustering(self.categories.instances,
                                    self.categories.assigned_categories)
            clustering.generateClustering(self.clustering_exp.getOutputDirectory(),
                                          None, None)
        else:
            self.clustering_exp = None
