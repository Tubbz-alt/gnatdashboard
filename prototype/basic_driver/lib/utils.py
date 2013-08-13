#! /usr/bin/env python

import json

## Violation #################################################################
##
class Violation(object):
    """Represent a rule violation from GNAT Tool's analysis

       For now this Object is only use by Codepeer report generator, might be
       re-arrange after the definition of the standard output format.
    """
    def __init__(self, prj, directory, src, line, rule_key, msg):
        """Initialize the object with the following arguments:

          - project: root project which is analysed
          - directory: logic directory of the source file
          - source: source file basename
          - rule key: Identification of the rule, the same that is mentionned in
                      the Tool's Sonar rule repository.
          - message: violation's message
        """
        self.prj = prj
        self.directory = directory
        self.src = src
        self.line = line
        self.rule_key = rule_key
        self.msg = msg
        # See TN L919-022
        #self.priority= priority

    def reprJSON(self):
        return dict(prj=self.prj, directory=self.directory, src=self.src,
                    line=self.line, rule_key=self.rule_key, msg=self.msg)


## Project #################################################################
##
class Project(object):
    """Represent a project

      /!\ This implementation of a source file must be changed for not
          prototype version.
    """

    def __init__(self, name):
        self.name = name


## Directory #################################################################
##
class Directory(object):
    """Represent a directory"""
    def __init__(self, dir_name, project):
        #Retrieve the name of the directory without the full path
        self.dir_name = dir_name.split('/')[-1]
        self.parent_project = Project(project)

    def get_parent_name(self):
        return self.parent_project.name


## Source #################################################################
##
class Source(object):
    """Represent a source file

      /!\ This implementation of a source file must be changed for not
          prototype version.
    """

    def __init__(self, base_name, directory, project, obj_dir):
        self.base_name = base_name
        self.full_name = directory + '/' + base_name
        self.obj_dir = obj_dir
        self.parent_dir = Directory(directory, project)

    def get_project(self):
        return self.parent_dir.get_parent_name()

    def get_directory(self):
        return self.parent_dir.dir_name

    def get_full_name(self):
        """"""
        return self.full_name


## SourceMap #################################################################
##
class SourceMap(object):
    """Map a source file with its project and directory """

    def __init__(self, project_tree_path):
        """Initializes the class """
        self.src_map = self.__parse_project_tree(project_tree_path)

    def __parse_project_tree(self, project_tree_path):
        """Parse the json file that contains project tree

           Save the informations in a dictionnary where the key is the
           source basename and the value is the corresponding Source object.
        """
        OBJ_DIR_KEY = 'Object_Dir'
        SRC_DIR_KEY = 'Source_Dirs'
        src_map = dict()
        with open(project_tree_path, 'r') as json_tree:
            output = json_tree.read()
            source_tree = json.loads(output)
            for prj in source_tree:
                obj_dir = None
                # If  the project has an object directory
                if len(source_tree[prj]) > 1:
                    obj_dir = source_tree[prj][OBJ_DIR_KEY]
                for src_dir in source_tree[prj][SRC_DIR_KEY]:
                    for src in source_tree[prj][SRC_DIR_KEY][src_dir]:
                        source = Source(src, src_dir, prj, obj_dir)
                        src_map[src] = source
        return src_map

    def get_path(self, src):
        """Return the source full path"""
        return self.src_map[src].get_full_name()

    def get_directory(self, src):
        """"""
        return self.src_map[src].get_directory()

    def get_project(self, src):
        """Return the project the source blongs"""
        return self.src_map[src].get_project()

    def get_source(self, src_name):
        return self.src_map[src_name]

    def get_obj_dir(self, src):
        return self.src_map[src].obj_dir

    def get_all_basename(self):
        return self.src_map.keys()

## Report #########################################################################
##
class Report(object):

    def __init__(self):
        self.violations = []

    def add_violation(self, violation):
        self.violations.append(violation)

    def reprJSON(self):
        return dict(errors=self.violations)


## ComplexEncoder #################################################################
##
class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        return obj.reprJSON()


## ReportExporter #################################################################
##

class ReportExporter(object):

    def export_report(self, report_path, report):
        with open(report_path, 'w+') as json_report:
            json_report.write(json.dumps(report.reprJSON(), cls=ComplexEncoder))