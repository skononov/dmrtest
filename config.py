import json
from tasks import DTScenario
import tasks
import dtglobals as dtg
from os import getenv
from singleton import Singleton
from traceback import print_exc

__appname__ = 'DMR TEST'
__version__ = '0.1'


class DTConfiguration(metaclass=Singleton):
    """
    Configuration manager for the DMR TESTER GUI.

    Scenario is a list of tasks with parameters.
    """
    __dtrcFilename = getenv('HOME') + '/dmr/config.json'

    def __init__(self, filename=None):
        self.config = dict()
        self.load(filename)

    def load(self, filename=None):
        if filename is None and self.__dtrcFilename is not None:
            filename = self.__dtrcFilename

        try:
            with open(filename, 'r', encoding='utf-8') as file:
                self.config = json.load(file)

        except Exception:
            print('DTConfiguration.load():', f'Could not read configuration from {filename}')
            self.config = dict()
            return False

        nscenarios = 0
        if 'scenarios' in self.config and isinstance(self.scenarios, list):
            for scendict in self.scenarios:
                try:
                    DTScenario.from_dict(scendict)
                except Exception:
                    print_exc()
                else:
                    nscenarios += 1

        if 'language' in self.config and self.config['language'] in ('ru', 'en'):
            dtg.LANG = self.config['language']
        else:
            dtg.LANG = 'ru'
        print(f'Configuration loaded from {filename} with {nscenarios} scenarios')

        return True

    def save(self, filename=None):
        try:
            if filename is None and self.__dtrcFilename is not None:
                filename = self.__dtrcFilename
            self.config['scenarios'] = [scenario.to_dict() for scenario in tasks.dtAllScenarios.values()]
            self.config['language'] = dtg.LANG
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(self.config, file, indent=2)
            print(f'Configuration saved to {filename} with {len(self.scenarios)} scenarios')
        except Exception:
            print('DTConfiguration.save():', f'{filename}: could not open file for writing')
            print_exc()

    @property
    def scenarios(self):
        return self.config['scenarios']
