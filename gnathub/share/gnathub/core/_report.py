# GNAThub (GNATdashboard)
# Copyright (C) 2016, AdaCore
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

"""GNAThub reporters

It massages the collected results of the various input tools in a common format
prior to export.
"""

import GNAThub

import collections
import os
import time

from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import HtmlFormatter


class _HtmlFormatter(HtmlFormatter):
    """Custom implementation of the Pygments' HTML formatter"""

    def wrap(self, source, _):
        # The default wrap() implementation adds a <div> and a <pre> tag.
        return source


class ReportBuilder(object):
    """Report builder"""

    def __init__(self):
        rules = GNAThub.Rule.list()
        tools = GNAThub.Tool.list()
        self._rules_by_id = {rule.id: rule for rule in GNAThub.Rule.list()}
        self._tools_by_id = {tool.id: tool for tool in tools}
        self._tools_by_name = {tool.name.lower(): tool for tool in tools}

    def _generate_source_tree(self, transform=None):
        """Generate the initial project structure

        {
            "project_name_1": {
                "source_dir_path_1": [
                    "source_filename_1", "source_filename_2"
                ],
                ...
            },
            ...
        }

        This structure will then be populated with relevant metrics.

        :param transform: optional routine that takes 3 parameters as input
            (the project name, the source directory full path, and the source
            filename) and returns any structure. This callback is used to
            populate the lists at the bottom of the above structure.  Defaults
            to returning the source filename.
        :type transform: Function | None
        :return: a dictionary listing the project sources
        :rtype: dict[str,dict[str,list[str]]]
        """

        def reduce_source_dirs(sources):
            """Compute the list of source directories from source files

            :param sources: the list of source files' absolute path
            :type sources: list[str]
            :return: the list of unique source directories' absolute path
            :rtype: list[str]
            """

            return list(set((
                os.path.normpath(os.path.dirname(f)) for f in sources
            )))

        transform = transform or (
            # Default to returning the filename if |transform| is not provided
            lambda project_name, source_dir, filename: filename
        )

        # TODO(charly): it might be worth considering exporting this function
        # or a more generic version of it from the GNAThub module.
        return {
            project: {
                directory: [
                    transform(project, directory, os.path.basename(path))
                    for path in sources
                    if os.path.normpath(os.path.dirname(path)) == directory
                ] for directory in reduce_source_dirs(sources)
            }
            for project, sources in GNAThub.Project.source_files().items()
            if sources
        }

    @classmethod
    def _decorate_dict(cls, obj, extra=None):
        """Decorate a Python dictionary with additional properties

        :param obj: the Python dictionary to decorate
        :type obj: dict[str,*]
        :param extra: extra fields to decorate the encoded object with
        :type extra: dict | None
        :rtype: dict[str,*]
        """
        if extra:
            obj.update(extra)
        return obj

    @classmethod
    def _encode_tool(cls, tool, extra=None):
        """JSON-encode a tool

        :param tool: the tool to encode
        :type tool: GNAThub.Tool
        :param extra: extra fields to decorate the encoded object with
        :type extra: dict | None
        :rtype: dict[str,*]
        """

        return cls._decorate_dict({
            'id': tool.id,
            'name': tool.name
        }, extra)

    @classmethod
    def _encode_rule(cls, rule, tool, extra=None):
        """JSON-encode a rule

        :param rule: the rule to encode
        :type rule: GNAThub.Rule
        :param tool: the tool associated with the rule
        :type tool: GNAThub.Tool
        :param extra: extra fields to decorate the encoded object with
        :type extra: dict | None
        :rtype: dict[str,*]
        """

        return cls._decorate_dict({
            'id': rule.id,
            'identifier': rule.identifier,
            'name': rule.name,
            'kind': rule.kind,
            'tool': cls._encode_tool(tool)
        }, extra)

    @classmethod
    def _encode_message_property(cls, prop, extra=None):
        """JSON-encode a message property

        :param prop: the property associated with the message
        :type prop: GNAThub.Property
        :param extra: extra fields to decorate the encoded object with
        :type extra: dict | None
        :rtype: dict[str,*]
        """
        return cls._decorate_dict({
            'id': prop.id,
            'identifier': prop.identifier,
            'name': prop.name
        }, extra)

    @classmethod
    def _encode_message(cls, msg, rule, tool, extra=None):
        """JSON-encode a message

        :param msg: the message to encode
        :type msg: GNAThub.Message
        :param rule: the rule associated with the message
        :type rule: GNAThub.Rule
        :param tool: the tool associated with the rule
        :type tool: GNAThub.Tool
        :param extra: extra fields to decorate the encoded object with
        :type extra: dict | None
        :rtype: dict[str,*]
        """

        return cls._decorate_dict({
            'begin': msg.col_begin,
            'end': msg.col_end,
            'rule': cls._encode_rule(rule, tool),
            'properties': [
                cls._encode_message_property(prop)
                for prop in msg.get_properties()
            ],
            'message': msg.data
        }, extra)

    def generate_src_hunk(self, project_name, source_file):
        """Generate the JSON-encoded representation of `source_file`

        :param project_name: the name of the project the source if from
        :type project_name: str
        :param source_file: the full path to the source file
        :type source_file: str
        :return: the JSON-encoded representation of `source_file`
        :rtype: dict[str,*]
        :raise: IOError
        """

        assert os.path.isfile(source_file), '{}: not such file ({})'.format(
            os.path.basename(source_file), source_file
        )

        messages_from_db = GNAThub.Resource.get(source_file).list_messages()

        tools, rules, properties = {}, {}, {}
        messages = collections.defaultdict(list)
        coverage = collections.defaultdict(str)

        for msg in messages_from_db:
            rule = self._rules_by_id[msg.rule_id]
            tool = self._tools_by_id[rule.tool_id]

            for prop in msg.get_properties():
                if prop.id not in properties:
                    properties[prop.id] = self._encode_message_property(prop, {
                        'message_count': 1
                    })
                else:
                    properties[prop.id]['message_count'] += 1

            if msg.line != 0:
                # Increment the count of inline messages
                if tool.id not in tools:
                    tools[tool.id] = self._encode_tool(tool, {
                        'message_count': 1
                    })
                else:
                    tools[tool.id]['message_count'] += 1
                if rule.id not in rules:
                    rules[rule.id] = self._encode_rule(rule, tool, {
                        'message_count': 1
                    })
                else:
                    rules[rule.id]['message_count'] += 1

            if rule.identifier != 'coverage':
                messages[msg.line].append(
                    self._encode_message(msg, rule, tool)
                )
            elif tool.name == 'gcov':
                coverage[msg.line] = (
                    'COVERED' if int(msg.data) else 'NOT_COVERED'
                )
            else:
                pass  # TODO(delay): add support for GNATcoverage

        src_hunk = {
            'project': project_name,
            'filename': os.path.basename(source_file),
            'metrics': messages[0],
            'properties': properties,
            'tools': tools,
            'rules': rules,
            'lines': None
        }

        # Custom HTML formatter outputting an array of HTMLified line of code.
        formatter = _HtmlFormatter()

        try:
            with open(source_file, 'r') as infile:
                content = infile.read()

            lexer = guess_lexer_for_filename(source_file, content)
            highlighted = highlight(content, lexer, formatter).splitlines()

            src_hunk['lines'] = [{
                'number': no,
                'content': line,
                'html_content': highlighted[no - 1],
                'coverage': coverage[no],
                'messages': messages[no]
            } for no, line in enumerate(content.splitlines(), start=1)]
        except IOError:
            self.log.exception('failed to read source file: %s', source_file)
            self.warn('failed to read source file: %s', source_file)
            self.warn('report might be incomplete')
        finally:
            return src_hunk

    def generate_index(self):
        """Generate the report index

        The index contains top-level information such as project name, database
        location, ... as well as the list of sub-project and their source
        directories and source files, along with some important metrics.

        :return: the JSON-encoded index
        :rtype: dict[str,*]
        """

        def _aggregate_metrics(project, source_dir, filename):
            """Collect metrics about the given source file

            :param project: the name of the project the source belongs to
            :type project: str
            :param source_dir: the full path to the source directory containing
                the source file
            :type source_dir: str
            :param filename: the basename of the source file
            :type filename: str
            :return: the dictionary containing metrics for `filename`
            :rtype: dict[str,*]
            """

            # Computes file-level metrics
            resource = GNAThub.Resource.get(os.path.join(source_dir, filename))
            metrics, msg_count = [], 0
            if resource:
                for msg in resource.list_messages():
                    rule = self._rules_by_id[msg.rule_id]
                    tool = self._tools_by_id[rule.tool_id]
                    # Note: the DB schema is currently designed so that metrics
                    # are stored has messages, and file metrics are attached to
                    # line 0.
                    if msg.line == 0:
                        metrics.append(self._encode_message(msg, rule, tool))
                    elif rule.identifier != 'coverage':
                        msg_count += 1

            return {
                'filename': filename,
                'metrics': metrics or None,
                'message_count': msg_count,
                '_associated_resource': resource is not None
            }

        return {
            'modules': self._generate_source_tree(_aggregate_metrics),
            'project': GNAThub.Project.name(),
            'creation_time': int(time.time()),
            'tools': [
                self._encode_tool(tool)
                for tool in self._tools_by_id.itervalues()
            ],
            'rules': [
                self._encode_rule(rule, self._tools_by_id[rule.tool_id])
                for rule in self._rules_by_id.itervalues()
            ],
            'properties': [
                self._encode_message_property(prop)
                for prop in GNAThub.Property.list()
            ],
            '_database': GNAThub.database()
        }
