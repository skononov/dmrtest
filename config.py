import os, json
from exception import *

class DTConfiguration:
    """
    Configuration manager for the DMR TESTER GUI
    """
    __dtrcFilename = '~/.dmrtestconf.json'
    
    def __init__(self):
        self.config = dict(scenarios={}, parameters={})
        self.read(DTConfiguration.__dtrcFilename)
    
    def read(self, filename):
        try:
            with open(filename, 'r') as file:
                self.config = json.load(file)
            print(f'Configuration loaded from {filename}')
        except:
            raise DTException(f'DTConfiguration.read(): {filename}: could not open file for reading')

    def write(self, filename):
        try:
            with open(filename, 'w') as file:
                json.dump(self.config, file)
            print(f'Configuration saved to {filename}')
        except:
            raise DTException(f'DTConfiguration.write(): {filename}: could not open file for writing')

    @property
    def scenarios(self):
        return self.config['scenarios']

    @property
    def parameters(self):
        return self.config['parameters']

    def scenario(self, name):
        try:
            return self.config['scenarios'][name]
        except KeyError:
            raise DTException(f'DTConfiguration.scenario(): scenario "{name}" is not defined')

    def add_task(self, scenario, task):
        try:
            if self.config['scenarios'][scenario] is None:
                self.config['scenarios'][scenario] = list()
            self.config['scenarios'][scenario].append(task)
        except KeyError:
            raise DTException(f'DTConfiguration.add_task(): scenario "{scenario}" is not defined')

    def del_scenario(self, name):
        try:
            del self.config['scenarios'][name]
        except KeyError:
            raise DTException(f'DTConfiguration.del_scenario(): no scenario "{name}" defined.')

    def clear_scenarios(self):
        self.config['scenarios'] = {}

    def set_parameter_limits(self, task, param, minval, maxval):
        if task not in self.config['parameters']:
            self.config['parameters'][task] = dict()
        self.config['parameters'][task][param] = dict(minValue=minval, maxValue=maxval)

    def del_parameter(self, task, param):
        try:
            del self.config['parameters'][task][param]
        except KeyError:
            raise DTException(f'DTConfiguration.del_parameter(): no task "{task}" or parameter "{param}" defined.')
