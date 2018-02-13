import logging

import yaml

logger = logging.getLogger(__name__)


class YamlFile():
    def __init__(self, file_name):
        self.file_name = file_name

    def parse(self):
        self.data = self.yaml_data()
        logger.info('Read config:', self.data)
        return self.data

    def file_data(self):
        # TODO: Check if file exists
        return open(self.file_name).read()

    def yaml_data(self):
        return yaml.load(self.file_data())
