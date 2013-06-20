#########################################
#        Qualimetrics Basic  API        #
#########################################

import GPS
import os

## OutputParserMetaClass ######################################################
##
class OutputParserMetaClass(type):
    registered = dict()   # list of registered parsers

    def __new__(cls, name, bases, attrs):
        new_class = type.__new__(cls, name, bases, attrs)
        OutputParserMetaClass.registered[new_class.get_name()] = new_class
        return new_class

    def get_name(self):
        """Return the name of the parser, either from a "name" class
            attribute, or from the class name
        """
        return getattr(self, 'name', self.__name__).lower()

## OutputParser ##############################################################
##
class OutputParser(object):
    __metaclass__ = OutputParserMetaClass

    def __init__(self,child):
        self.child = child

    def on_stdout(self,text):
        if self.child != None:
            self.child.on_stdout (text)

    def on_stderr(self,text):
        if self.child != None:
           self.child.on_stderr (text)

    def on_exit(self,status=0):
        if self.child != None:
            self.child.on_exit (status)

## create_parser ######################################################
##
def create_parser(name, child=None):
    if OutputParserMetaClass.registered.has_key (name):
        return OutputParserMetaClass.registered[name](child)
    else:
        return None

## get_log_dir ######################################################
##
def get_log_dir():
    """/!\ Return qualimetrics logs directory /!\

       This value must be retrieved from the Ada program
    """
    logs_dir =  os.path.join(GPS.Project.root().object_dirs()[0],
                             'qualimetrics', 'logs')
    return logs_dir

## get_log_dir ######################################################
##
def get_plugin_dir():
    """"/!\ Return qualimetrics core plugins directory /!\

        This value must be retrieved from the Ada program
    """
    return
