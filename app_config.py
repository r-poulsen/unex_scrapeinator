''' Encapsulates an application configuration YAML file '''

import yaml


class AppConfig:
    """
    Class to encapsulate an application configuration YAML file.

    Args:
        config_file (str): Path to the configuration YAML file.

    Attributes:
        config (dict): Dictionary containing the loaded configuration.

    """

    def __init__(self, config_file):
        """
        Initialize the AppConfig object by loading the configuration from the specified YAML file.

        Args:
            config_file (str): Path to the configuration YAML file.

        """
        self.config = self.load_config(config_file)

    def load_config(self, config_file) -> dict | None:
        """
        Load the configuration from the specified YAML file.

        Args:
            config_file (str): Path to the configuration YAML file.

        Returns:
            dict: Dictionary containing the loaded configuration.

        Raises:
            yaml.YAMLError: If there is an error loading the YAML file.

        """
        with open(config_file, 'r', encoding='utf-8') as file:
            try:
                return yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(f"Error loading config file: {exc}")
                return None

    def get(self, key, default=None) -> any:
        """
        Retrieve a configuration value by key.

        Args:
            key (str): Key to retrieve the configuration value.
            default (optional): Default value to return if the key is not found. Defaults to None.

        Returns:
            Any: The configuration value corresponding to the key,
                or the default value if the key is not found.

        """
        keys = key.split('.')
        value = self.config
        for k in keys:

            if value is None:
                return default

            value = value.get(k)

        return value

    def override(self, key, value) -> any:
        """
        Override a configuration value with a new value.

        Args:
            key (str): Key to the configuration value to override.
            value (Any): New value to set for the configuration key.

        """
        keys = key.split('.')
        last_key = keys.pop()
        config = self.config
        for k in keys:
            config = config.setdefault(k, {})
        config[last_key] = value


if __name__ == "__main__":
    cfg = AppConfig(config_file="/home/rune/prog/xm3/xm3.yaml")
    print(cfg.get('paths.videos'))
    print(cfg.get('stash.translate_path'))
