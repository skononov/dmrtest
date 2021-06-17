import json
from dtexcept import DTError

__appname__ = 'DMR TEST'
__version__ = '0.1'


class DTConfiguration:
    """
    Configuration manager for the DMR TESTER GUI.

    Scenario is a dict of tasks with a task name being a key and dict of parameters being a value. Task parameters are
    stored as dictionaries with one obligatory element 'value' and two optional elements: 'minValue', 'maxValue'.
    """
    __dtrcFilename = '~/.dtconf.json'

    def __init__(self, filename=None):
        self.config = dict(scenarios={})
        if filename is not None:
            self.load(filename)
        else:
            self.load(DTConfiguration.__dtrcFilename)

    def load(self, filename):
        try:
            with open(filename, 'r') as file:
                self.config = json.load(file)
            print(f'Configuration loaded from {filename}')
        except Exception as exc:
            print(exc)
            print(f'DTConfiguration.load(): {filename}: could not open file for reading. Use default configuration.')

    def save(self, filename):
        try:
            with open(filename, 'w') as file:
                json.dump(self.config, file)
            print(f'Configuration saved to {filename}')
        except Exception as exc:
            raise DTError('DTConfiguration.save()', f'{filename}: could not open file for writing') from exc

    @property
    def scenarios(self):
        return self.config['scenarios']

    def scenario(self, name):
        try:
            return self.config['scenarios'][name]
        except KeyError as exc:
            raise DTError('DTConfiguration.scenario()', f'Scenario "{name}" is not defined') from exc

    def add_task(self, scenario, task, params=None):
        if params is None:
            params = dict()
        if scenario not in self.config['scenarios']:
            self.config['scenarios'][scenario] = {task: params}
        elif task in self.config['scenarios'][scenario]:
            print(f'DTConfiguration.add_task(): Task {task} is already defined for scenario {scenario}')
        else:
            self.config['scenarios'][scenario][task] = params

    def del_scenario(self, name):
        try:
            del self.config['scenarios'][name]
        except KeyError:
            print('DTConfiguration.del_scenario(): No scenario "{name}" defined.')

    def del_task(self, scenario, task):
        try:
            sctasks = self.config['scenarios'][scenario]
        except KeyError:
            raise DTError('DTConfiguration.del_task()', f'No scenario {scenario} defined.')
        else:
            for i, t in enumerate(sctasks):
                if task == t['task']:
                    sctasks.pop(i)
                    break

    def clear_scenarios(self):
        self.config['scenarios'] = {}

    def set_parameter(self, scenario, task, param, value, minval=None, maxval=None):
        scenarios = self.config['scenarios']
        if scenario in scenarios:
            if task not in scenarios[scenario]:
                scenarios[scenario][task] = dict()
            else:

                self.config['parameters'][task][param] = dict(value=value, minValue=minval, maxValue=maxval)

    def del_parameter(self, task, param):
        try:
            del self.config['parameters'][task][param]
        except KeyError:
            raise DTError('DTConfiguration.del_parameter()', f'No task "{task}" or parameter "{param}" defined.')
