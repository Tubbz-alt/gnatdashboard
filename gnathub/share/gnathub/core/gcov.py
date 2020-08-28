# GNAThub (GNATdashboard)
# Copyright (C) 2013-2017, AdaCore
#
# This is free software;  you can redistribute it  and/or modify it  under
# terms of the  GNU General Public License as published  by the Free Soft-
# ware  Foundation;  either version 3,  or (at your option) any later ver-
# sion.  This software is distributed in the hope  that it will be useful,
# but WITHOUT ANY WARRANTY;  without even the implied warranty of MERCHAN-
# TABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for  more details.  You should have  received  a copy of the GNU
# General  Public  License  distributed  with  this  software;   see  file
# COPYING3.  If not, go to http://www.gnu.org/licenses for a complete copy
# of the license.

"""GNAThub plug-in for the Gcov command-line tool.

It exports the Gcov class which implements the :class:`GNAThub.Plugin`
interface.  This allows GNAThub's plug-in scanner to automatically find this
module and load it as part of the GNAThub default execution.
"""

import os
import re

import GNAThub
from GNAThub import Console, Plugin, Reporter


class Gcov(Plugin, Reporter):
    """Gcov plugin for GNAThub.

    Retrieves .gcov generated files from the project root object directory,
    parses them and feeds the database with the data collected from each files.
    """

    GCOV_EXT = '.gcov'

    def __init__(self):
        super(Gcov, self).__init__()

        self.tool = None
        self.rule = None

        # A dictionary containing all messages, to allow bulk insertion in the
        # database: key is an string representing the number of hits,
        # value is the corresponding Message instance.
        self.hits = {}

        # List of resource messages suitable for tool level bulk insertion
        self.resources_messages = []

        self.matcher = re.compile("^\s*(.*):\s*(\d+):.*")

    def __process_file(self, resource, filename, resources_messages):
        """Processe one file, adding in bulk all coverage info found.

        :param GNAThub.Resource resource: the resource being processed
        :param str filename: the name of the resource
        """

        message_data = []

        with open(filename, 'r') as gcov_file:
            # Retrieve information for every source line.
            # Skip the first 2 lines.

            for line in gcov_file.readlines()[2:]:
                matches = self.matcher.match(line)

                if not matches:
                    continue

                (hits, line) = matches.groups()

                # Skip lines that do not contain coverage info
                if hits == '-':
                    continue

                # Line is not covered
                if hits == '#####' or hits == '=====':
                    hits = '0'

                line = int(line)

                # Find the message corresponding to this hits number

                if hits in self.hits:
                    msg = self.hits[hits]
                else:
                    msg = GNAThub.Message(self.rule, hits)
                    self.hits[hits] = msg

                message_data.append([msg, line, 1, 1])

        # Preparing list for tool level insertion of resources messages
        resources_messages.append([resource, message_data])

    def report(self):
        """Analyse the report files generated by :program:`Gcov`.

        Finds all .gcov files in the object directory and parses them.

        Sets the exec_status property according to the success of the analysis:

            * ``GNAThub.EXEC_SUCCESS``: on successful execution and analysis
            * ``GNAThub.EXEC_FAILURE``: on any error
        """

        # Clear existing references only if not incremental run
        if not GNAThub.incremental():
            self.log.info('clear existing results if any')
            GNAThub.Tool.clear_references(self.name)

        self.info('parse coverage reports (%s)' % self.GCOV_EXT)

        # Handle multiple object directories
        if GNAThub.Project.object_dirs():
            # If there are object directories defined in the project tree, look
            # for .gcov files there.

            files = []
            for obj_dir in GNAThub.Project.object_dirs():
                # Fetch all files in project object directories and retrieve
                # only .gcov files, absolute path
                for filename in os.listdir(obj_dir):
                    if filename.endswith(self.GCOV_EXT):
                        files.append(os.path.join(obj_dir, filename))

        else:
            # If any object directory is defined in .gpr, fetch all files in
            # default project object directory and retrieve only .gcov files,
            # absolute path
            prj_object_dir = GNAThub.Project.artifacts_dir()
            files = [os.path.join(prj_object_dir, filename)
                     for filename in os.listdir(prj_object_dir)
                     if filename.endswith(self.GCOV_EXT)]

        # If no .gcov file found, plugin returns on failure
        if not files:
            self.error('no %s file in object directory' % self.GCOV_EXT)
            return GNAThub.EXEC_FAILURE

        self.tool = GNAThub.Tool(self.name)
        self.rule = GNAThub.Rule('coverage', 'coverage',
                                 GNAThub.METRIC_KIND, self.tool)

        total = len(files)

        # List of resource messages suitable for tool level bulk insertion
        resources_messages = []

        try:
            for index, filename in enumerate(files, start=1):
                # Retrieve source fullname (`filename` is the *.gcov report
                # file).

                base, _ = os.path.splitext(os.path.basename(filename))
                src = GNAThub.Project.source_file(base)

                resource = GNAThub.Resource.get(src)

                if resource:
                    self.__process_file(resource, filename, resources_messages)

                Console.progress(index, total, new_line=(index == total))

            # Tool level insert for resources messages
            self.tool.add_messages(resources_messages, [])

        except IOError as why:
            self.log.exception('failed to parse reports')
            self.error(str(why))
            return GNAThub.EXEC_FAILURE

        else:
            return GNAThub.EXEC_SUCCESS
