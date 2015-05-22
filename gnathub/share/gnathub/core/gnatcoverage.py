############################################################################
#                                                                          #
#                               G N A T h u b                              #
#                                                                          #
#                     Copyright (C) 2013-2015, AdaCore                     #
#                                                                          #
# This is free software;  you can redistribute it  and/or modify it  under #
# terms of the  GNU General Public License as published  by the Free Soft- #
# ware  Foundation;  either version 3,  or (at your option) any later ver- #
# sion.  This software is distributed in the hope  that it will be useful, #
# but WITHOUT ANY WARRANTY;  without even the implied warranty of MERCHAN- #
# TABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public #
# License for  more details.  You should have  received  a copy of the GNU #
# General  Public  License  distributed  with  this  software;   see  file #
# COPYING3.  If not, go to http://www.gnu.org/licenses for a complete copy #
# of the license.                                                          #
#                                                                          #
############################################################################

"""GNAThub plug-in for the GNATcoverage command-line tool

It exports the GNATcoverage class which implements the :class:`GNAThub.Plugin`
interface.  This allows GNAThub's plug-in scanner to automatically find this
module and load it as part of the GNAThub default execution.
"""

import os
import re

import GNAThub
from GNAThub import Console


class GNATcoverage(GNAThub.Plugin):
    """GNATcoverage plugin for GNAThub

    Retrieves .xcov generated files from the project root object directory,
    parses them and feeds the database with the data collected from each files.
    """

    GNATCOV_EXT = '.xcov'
    COV_LINE_RE = re.compile(r' *(?P<line_no>\d+) (?P<cov_char>[.0+!-]):.*')
    COV_SLOC_RE = re.compile(
        r'^(?P<cov_level>\w+) ".*" at (?P<line_no>\d+):(?P<col_no>\d+)'
        r' (?P<message>[^"]+)$'
    )

    def __init__(self):
        super(GNATcoverage, self).__init__()

        self.tool = None
        self.coverage_rule = None
        # Mapping: coverage level -> issue rule for this coverage.
        self.issue_rules = {}

        # A dictionary containing all messages, to allow bulk insertion in the
        # database: key is an string representing the number of hits,
        # value is the corresponding Message instance.
        self.hits = {}

    def __process_file(self, resource, filename):
        """Processes one file, adding in bulk all coverage info found

        :param resource: the resource being processed
        :type resource: GNAThub.Resource
        :param filename: the name of the resource
        :type filename: str
        """

        bulk_messages = []

        def add_message(rule, message, line_no, column_no):
            bulk_messages.append([
                GNAThub.Message(rule, message),
                line_no, column_no, column_no,
            ])

        with open(filename, 'r') as gnatcov_file:
            # Retrieve information for every source line.
            lines_iter = iter(gnatcov_file)

            # Skip the first 3 lines (they specify source file path, coverage
            # ratio and coverage level).
            for _ in range(3):
                next(lines_iter)

            line_no = None
            column_no = None

            for line in lines_iter:
                line = line.rstrip()
                m = self.COV_LINE_RE.match(line)

                column_no = None
                message = None

                if m:
                    line_no = int(m.group('line_no'))
                    cov_char = m.group('cov_char')
                    if cov_char == '+':
                        add_message(self.coverage_rule, '1', line_no, 1)
                else:
                    m = self.COV_SLOC_RE.match(line)
                    assert m
                    assert int(m.group('line_no')) == line_no
                    column_no = int(m.group('col_no'))
                    message_label = m.group('message')

                    # Insert one message for coverage reports and another one
                    # for issue reports.
                    add_message(self.coverage_rule, '0',
                                line_no, column_no)
                    cov_level = {
                        'statement': 'stmt',
                        'decision':  'decision',
                        'condition': 'mcdc',
                    }[m.group('cov_level')]
                    add_message(self.issue_rules[cov_level], message_label,
                                line_no, column_no)

        resource.add_messages(bulk_messages)

    def __parse_gnatcov_report(self):
        """Analyses the report files generated by :program:`GNATcoverage`

        Finds all .xcov files in the object directory and parses them.

        Sets the exec_status property according to the success of the
        analysis:

            * ``GNAThub.EXEC_SUCCESS``: on successful execution and analysis
            * ``GNAThub.EXEC_FAILURE``: on any error
        """

        self.info('parse coverage reports (%s)' % self.GNATCOV_EXT)

        # Fetch all files in project object directory and retrieve only
        # .xcov files, absolute path
        files = [os.path.join(GNAThub.Project.object_dir(), filename)
                 for filename in os.listdir(GNAThub.Project.object_dir())
                 if filename.endswith(self.GNATCOV_EXT)]

        # If no .xcov file found, plugin returns on failure
        if not files:
            self.error('no %s file in object directory' % self.GNATCOV_EXT)
            self.exec_status = GNAThub.EXEC_FAILURE
            return

        self.tool = GNAThub.Tool(self.name)
        self.coverage_rule = GNAThub.Rule('coverage', 'coverage',
                                          GNAThub.METRIC_KIND, self.tool)
        for cov_level in ('stmt', 'decision', 'mcdc'):
            name = 'gnatcov_{}'.format(cov_level)
            self.issue_rules[cov_level] = GNAThub.Rule(
                name, name, GNAThub.RULE_KIND, self.tool
            )

        total = len(files)

        try:
            for index, filename in enumerate(files, start=1):
                # Retrieve source fullname (`filename` is the *.xcov report
                # file).
                base, _ = os.path.splitext(os.path.basename(filename))
                src = GNAThub.Project.source_file(base)

                resource = GNAThub.Resource.get(src)

                if resource:
                    self.__process_file(resource, filename)

                Console.progress(index, total, new_line=(index == total))

        except (IOError, ValueError) as why:
            self.exec_status = GNAThub.EXEC_FAILURE
            self.log.exception('failed to parse GNATcoverage reports')
            self.error(str(why))

        else:
            self.exec_status = GNAThub.EXEC_SUCCESS

    def execute(self):
        """Finds the GNATcoverage output files and parses them"""
        self.__parse_gnatcov_report()