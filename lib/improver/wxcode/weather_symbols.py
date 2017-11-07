# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017 Met Office.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Module containing weather symbol implementation."""


import numpy as np
import copy
import iris
from iris import Constraint

from improver.wxcode.wxcode_utilities import (add_wxcode_metadata,
                                              expand_nested_lists)
from improver.wxcode.wxcode_decision_tree import wxcode_decision_tree


class WeatherSymbols(object):
    """
    Definition and implementation of a weather symbol decision tree. This
    plugin uses a variety of diagnostic inputs and the decision tree logic
    to determine the most representative weather symbol for each site
    defined in the input cubes.
    """

    def __init__(self):
        """
        Define a decision tree for determining weather symbols based upon
        the input diagnostics. Use this decision tree to allocate a weather
        symbol to each point.
        """
        self.queries = wxcode_decision_tree()

    def __repr__(self):
        """Represent the configured plugin instance as a string."""
        return '<WeatherSymbols>'

    def check_input_cubes(self, cubes):
        """
        Check that the input cubes contain all the diagnostics and thresholds
        required by the decision tree.

        Args:
            cubes (iris.cube.CubeList):
                A CubeList containing the input diagnostic cubes.

        Raises:
            IOError:
                Raises an IOError if any of the required input data is missing.
                The error includes details of which fields are missing.
        """
        missing_data = []
        for query in self.queries.itervalues():
            diagnostics = expand_nested_lists(query, 'diagnostic_fields')
            thresholds = expand_nested_lists(query, 'diagnostic_thresholds')
            conditions = expand_nested_lists(query, 'diagnostic_conditions')
            for diagnostic, threshold, condition in zip(
                    diagnostics, thresholds, conditions):

                threshold = threshold.points.item()
                test_condition = (
                    Constraint(
                        name=diagnostic,
                        coord_values={'threshold': threshold},
                        cube_func=lambda cube: (
                            cube.attributes['relative_to_threshold'] ==
                            condition)))

                if not cubes.extract(test_condition):
                    missing_data.append([diagnostic, threshold, condition])

        if missing_data:
            msg = ('Weather Symbols input cubes are missing'
                   ' the following required'
                   ' input fields:\n')
            dyn_msg = 'name: {}, threshold: {}, relative_to_threshold: {}\n'
            for item in missing_data:
                msg = msg + dyn_msg.format(*item)
            raise IOError(msg)
        return

    @staticmethod
    def invert_condition(test_conditions):
        """
        Invert a comparison condition to select the negative case.

        Args:
            test_conditions (dict):
                A single query from the decision tree.
        Returns:
            (tuple): tuple containing:
                **inverted_threshold** (string):
                    A string representing the inverted comparison.
                **inverted_combination** (string):
                    A string representing the inverted combination
        """
        threshold = test_conditions['threshold_condition']
        inverted_threshold = threshold
        if threshold == '>=':
            inverted_threshold = '<'
        if threshold == '<=':
            inverted_threshold = '>'
        if threshold == '<':
            inverted_threshold = '>='
        if threshold == '>':
            inverted_threshold = '<='
        combination = test_conditions['condition_combination']
        inverted_combination = combination
        if combination == 'OR':
            inverted_combination = 'AND'
        elif combination == 'AND':
            inverted_combination = 'OR'

        return inverted_threshold, inverted_combination

    @staticmethod
    def construct_condition(extract_constraint, condition,
                            probability_threshold, gamma):
        """
        Create a string representing a comparison condition.

        Args:
            extract_constraint (iris.Constraint or list of Constraints):
                An iris constraint that will be used to extract the correct
                diagnostic cube (by name) from the input cube list and the
                correct threshold from that cube.
            condition (string):
                The condition statement (e.g. greater than, >).
            probability_threshold (float):
                The probability value to use in the comparison.
            gamma (float or None):
                The gamma factor to multiply one field by when performing
                a subtraction. This value will be None in the case that
                extract_constraint is not a list; it will not be used.
        Returns:
            string:
                The formatted condition statement,
                e.g. cubes.extract(Constraint(
                         name='probability_of_rainfall_rate',
                         coord_values={'threshold': 0.03})
                     )[0].data < 0.5)
        """
        if isinstance(extract_constraint, list):
            return ('(cubes.extract({})[0].data - cubes.extract({})[0].data * '
                    '{}) {} {}'.format(
                        extract_constraint[0], extract_constraint[1], gamma,
                        condition, probability_threshold))
        return 'cubes.extract({})[0].data {} {}'.format(
            extract_constraint, condition, probability_threshold)

    @staticmethod
    def format_condition_chain(conditions, condition_combination='AND'):
        """
        Chain individual condition statements together in a format that
        numpy.where can use to make a series of comparisons.

        Args:
            conditions (list):
                A list of conditions to be combined into a single comparison
                statement.
            condition_combination (string):
                The method by which multiple conditions should be combined,
                either AND or OR.
        Returns:
            string:
                A string formatted as a chain of conditions suitable for use in
                a numpy.where statement.
                e.g. (condition 1) & (condition 2)
        """
        if condition_combination == 'OR':
            return ('({}) | '*len(conditions)).format(*conditions).strip('| ')
        return ('({}) & '*len(conditions)).format(*conditions).strip('& ')

    @staticmethod
    def create_condition_chain(test_conditions):
        """
        A wrapper to call the construct_condition function for all the
        conditions specfied in a single query.

        Args:
            test_conditions (dict):
                A query from the decision tree.
        Returns:
            condition_chain (list):
                A list of strings that describe the conditions comprising the
                query.
                e.g.
                [
                  "(cubes.extract(Constraint(
                        name='probability_of_rainfall_rate',
                        coord_values={'threshold': 0.03})
                   )[0].data < 0.5) |
                   (cubes.extract(Constraint(
                        name='probability_of_lwe_snowfall_rate',
                        coord_values={'threshold': 0.03})
                   )[0].data < 0.5)"
                ]
        """
        conditions = []
        loop = 0
        for diagnostic, p_threshold, d_threshold in zip(
                test_conditions['diagnostic_fields'],
                test_conditions['probability_thresholds'],
                test_conditions['diagnostic_thresholds']):

            gamma = test_conditions.get('diagnostic_gamma')
            if gamma is not None:
                gamma = gamma[loop]
            loop += 1

            extract_constraint = WeatherSymbols.construct_extract_constraint(
                diagnostic, d_threshold)
            conditions.append(
                WeatherSymbols.construct_condition(
                    extract_constraint, test_conditions['threshold_condition'],
                    p_threshold, gamma))
        condition_chain = WeatherSymbols.format_condition_chain(
            conditions,
            condition_combination=test_conditions['condition_combination'])
        return [condition_chain]

    @staticmethod
    def construct_extract_constraint(diagnostics, thresholds):
        """
        Construct an iris constraint.

        Args:
            diagnostics (string or list of strings):
                The names of the diagnostics to be extracted from the CubeList.
            thresholds (iris.AuxCoord or list of iris.AuxCoord):
                A thresholds within the given diagnostic cubes that are needed.
                Including units.
        Returns:
            iris.Constraint or list of iris.Constraints:
                The constructed iris constraints.
        """

        if isinstance(diagnostics, list):
            constraints = []
            for diagnostic, threshold in zip(diagnostics, thresholds):
                threshold = threshold.points.item()
                constraints.append(iris.Constraint(
                    name=diagnostic,
                    coord_values={'threshold': threshold}))
            return constraints
        threshold = thresholds.points.item()
        return iris.Constraint(
            name=diagnostics, coord_values={'threshold': threshold})

    @staticmethod
    def find_all_routes(graph, start, end, route=None):
        """
        Function to trace all routes through the decision tree.

        Args:
            graph (dict):
                A dictionary that describes each node in the tree,
                e.g. {<node_name>: [<succeed_name>, <fail_name>]}
            start (string):
                The node name of the tree root (currently always
                significant_precipitation).
            end (int):
                The weather symbol code to which we are tracing all routes.

        Returns:
            routes (list):
                A list of node names that defines the route from the tree root
                to the weather symbol leaf (end of chain).

        References:
            Method based upon Python Patterns - Implementing Graphs essay
            https://www.python.org/doc/essays/graphs/
        """
        if route is None:
            route = []

        route = route + [start]
        if start == end:
            return [route]
        if start not in graph.keys():
            return []

        routes = []
        for node in graph[start]:
            if node not in route:
                newroutes = WeatherSymbols.find_all_routes(graph, node, end,
                                                           route)
                for newroute in newroutes:
                    routes.append(newroute)
        return routes

    @staticmethod
    def create_symbol_cube(cube):
        """
        Create an empty weather_symbol cube initialised with -1 across the
        grid.

        Args:
            cube (iris.cube.Cube):
                An x-y slice of one of the input cubes, used to define the
                size of the weather symbol grid.
        Returns:
            symbols (iris.cube.Cube):
                A cube full of -1 values, with suitable metadata to describe
                the weather symbols that will fill it.
        """
        cube_format = next(cube.slices_over(['threshold']))
        symbols = cube_format.copy(data=np.full(cube_format.data.shape, -1,
                                                dtype=np.int))

        symbols.remove_coord('threshold')
        symbols.attributes.pop('relative_to_threshold')
        symbols = add_wxcode_metadata(symbols)

        return symbols

    def process(self, cubes):
        """Apply the decision tree to the input cubes to produce weather
        symbol output.

        Args:
            cubes (iris.cube.CubeList):
                A cubelist containing the diagnostics required for the
                weather symbols decision tree, these at conincident times.

        Returns:
            symbols (iris.cube.Cube):
                A cube of weather symbols.
        """
        # Check input cubes contain required data
        self.check_input_cubes(cubes)

        # Construct graph nodes dictionary
        graph = {key: [self.queries[key]['succeed'], self.queries[key]['fail']]
                 for key in self.queries.keys()}

        # Search through tree for all leaves (weather code end points)
        defined_symbols = []
        for item in self.queries.itervalues():
            for value in item.itervalues():
                if isinstance(value, int):
                    defined_symbols.append(value)

        # Create symbol cube
        symbols = self.create_symbol_cube(cubes[0])

        # Loop over possible symbols
        for symbol_code in defined_symbols:
            routes = self.find_all_routes(graph, 'significant_precipitation',
                                          symbol_code)

            # Loop over possible routes from root to leaf
            for route in routes:
                # print ('--> {}' * len(route)).format(
                #    *[node for node in route])
                conditions = []
                for i_node in range(len(route)-1):
                    current_node = route[i_node]
                    current = copy.copy(self.queries[current_node])
                    try:
                        next_node = route[i_node+1]
                        next_data = copy.copy(self.queries[next_node])
                    except KeyError:
                        next_node = symbol_code

                    if current['fail'] == next_node:
                        (current['threshold_condition'],
                         current['condition_combination']) = (
                             self.invert_condition(current))

                    conditions.extend(self.create_condition_chain(current))

                test_chain = self.format_condition_chain(conditions)

                # Set grid locations to suitable weather symbol
                symbols.data[np.where(eval(test_chain))] = symbol_code

        return symbols
