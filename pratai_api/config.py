import ConfigParser

Config = ConfigParser.ConfigParser()
Config.read("/etc/pratai/pratai-api.conf")


# TODO(m3m0): this should be a library or replace it by oslo.config


def parse_config(section):
    """Parse a config file into a dict
    :param section: string
    :return: a dict representing a config file
    """
    config_dict = {}
    options = Config.options(section)
    for option in options:
        try:
            config_dict[option] = Config.get(section, option)
            if config_dict[option] == -1:
                print("skip: {0}".format(option))
        except Exception:
            print("exception on {0}!".format(option))
            config_dict[option] = None
    return config_dict
