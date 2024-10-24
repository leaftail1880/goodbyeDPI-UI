import configparser
import json
import logging
import os
import sys
import traceback
import winreg
from logger import AppLogger

DEBUG = False
DEBUG_PATH = os.path.dirname(os.path.abspath(__file__)).replace("\src", "/")

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = DEBUG_PATH

def is_font_installed(font_name):
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
        i = 0
        while True:
            try:
                value = winreg.EnumValue(registry_key, i)
                if font_name.lower() in value[0].lower():
                    return True
                i += 1
            except OSError:
                break
        return False
    except Exception:
        return False

DIRECTORY = f'{application_path}/_internal/' if not DEBUG else ''

VERSION = "1.2.0"

SETTINGS_FILE_PATH = DIRECTORY+'data/settings/settings.ini'
BACKUP_SETTINGS_FILE_PATH = DIRECTORY+'data/settings/_settings.ini'
CONFIG_PATH = DIRECTORY+'data/settings/presets'
LOCALE_FILE_PATH =  DIRECTORY+'data/loc/loc.ini'
GOODBYE_DPI_PATH =  DIRECTORY+'data/goodbyeDPI/'
GOODBYE_DPI_EXECUTABLE = "goodbyedpi.exe" 
ZAPRET_PATH = DIRECTORY+'data/zapret/'
ZAPRET_EXECUTABLE = "winws.exe" 
SPOOFDPI_EXECUTABLE = "spoofdpi-windows-amd64.exe" 
BYEDPI_EXECUTABLE = "ciadpi.exe" 
EXECUTABLES = {
    'goodbyeDPI':GOODBYE_DPI_EXECUTABLE,
    'zapret':ZAPRET_EXECUTABLE,
    'spoofdpi':SPOOFDPI_EXECUTABLE,
    'byedpi': BYEDPI_EXECUTABLE
}
COMPONENTS_URLS = {
    'goodbyeDPI':'ValdikSS/GoodbyeDPI',
    'zapret':'bol-van/zapret',
    'spoofdpi':'xvzc/SpoofDPI',
    'byedpi':'hufrea/byedpi'
}

FONT = 'Nunito SemiBold' if is_font_installed('Nunito SemiBold') else 'Segoe UI'
MONO_FONT = 'Cascadia Mono' if is_font_installed('Cascadia Mono') else 'Consolas'

PARAMETER_MAPPING = {
    'blockpassivedpi': '-p',
    'blockquic': '-q',
    'replacehost': '-r',
    'removespace': '-s',
    'mixhostcase': '-m',
    'donotwaitack': '-n',
    'additionalspace': '-a',
    'processallports': '-w',
    'allownosni': '--allow-no-sni',
    'dnsverbose': '--dns-verb',
    'wrongchecksum': '--wrong-chksum',
    'wrongseq': '--wrong-seq',
    'nativefrag': '--native-frag',
    'reversefrag': '--reverse-frag',
    'blacklist': '--blacklist',
}
VALUE_PARAMETERS = {
    'dns': '--dns-addr',
    'dns_port': '--dns-port',
    'dnsv6': '--dnsv6-addr',
    'dnsv6_port': '--dnsv6-port',
    'httpfragmentation': '-f',
    'httpkeepalive': '-k',
    'httpsfragmentation': '-e',
    'maxpayload': '--max-payload',
    'additionalport': '--port',
    'ipid': '--ip-id',
    'fakefromhex': '--fake-from-hex',
    'fakegen': '--fake-gen',
    'fakeresend': '--fake-resend',
    'autottl': '--auto-ttl',
    'minttl': '--min-ttl',
    'setttl': '--set-ttl',
        
}

S_PARAMETER_MAPPING = {
    'enabledoh': '-enable-doh',
    'ipv4only': '-dns-ipv4-only',
    'silent': '-silent',
    'systemproxy': '-system-proxy',
    'enabledebug': '-debug',
}

S_VALUE_PARAMETERS = {
    'addr': '-addr',
    'dns': '-dns-addr',
    'dnsport': '-dns-port',
    'port': '-port',
    'pattern': '-pattern',
    'timeout': '-timeout',
    'windowsize': '-window-size',
}



REPO_OWNER = "Storik4pro"
REPO_NAME = "goodbyeDPI-UI"
CONFIGS_REPO_NAME = "goodbyeDPI-UI-configs"

logger = AppLogger(VERSION, "settings_import")

class Settings:
    def __init__(self) -> None:
        self.settings = self.reload_settings()

    def change_setting(self, group, key, value):
        self.settings[group][key] = value

    def save_settings(self):
        with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as configfile:
            self.settings.write(configfile)

        self.reload_settings()
    
    def reload_settings(self):
        config = configparser.ConfigParser()
        config.read(SETTINGS_FILE_PATH, encoding='utf-8')
        self.settings = config
        return self.settings
try:    
    logger.create_logs(f"Importing application settings from \"{SETTINGS_FILE_PATH}\"")
    settings = Settings()
except Exception as ex: 
    error_message = traceback.format_exc()
    logger.raise_critical(error_message)


class Text:
    def __init__(self, language) -> None:
        self.inAppText = {'': ''}
        self.reload_text(language)

    def reload_text(self, language=None):
        self.selectLanguage = language if language else settings.settings['GLOBAL']['language'] 
        config = configparser.ConfigParser()
        config.read(LOCALE_FILE_PATH, encoding='utf-8')
        self.inAppText = config[f'{self.selectLanguage}']

try:    
    logger.create_logs(f"Importing application localize from \"{LOCALE_FILE_PATH}\"")
    text = Text(settings.settings['GLOBAL']['language'])
except Exception as ex: 
    error_message = traceback.format_exc()
    logger.raise_critical(error_message)

class UserConfig:
    def __init__(self, configfile) -> None:
        self.configfile = configfile
        self.data = self.reload_config()

    def reload_config(self):
        with open(self.configfile, 'r', encoding='utf-8') as file:
            self.data = json.load(file)
        return self.data

    def write_config(self):
        with open(self.configfile, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)
        self.data = self.reload_config()

    def copy_to(self, path):
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def get_value(self, key) -> str|bool|int:
        return self.data.get(key)
    
    def set_value(self, key, value):
        print(value, key)
        self.data[key] = value
        self.write_config()

try:
    goodbyedpi_config_path = os.path.join(settings.settings['CONFIG']['goodbyedpi_config_path'])
    zapret_config_path = os.path.join(settings.settings['CONFIG']['zapret_config_path'])
    byedpi_config_path = os.path.join(settings.settings['CONFIG']['byedpi_config_path'])
    spoofdpi_config_path = os.path.join(settings.settings['CONFIG']['spoofdpi_config_path'])
    
    configs = {
        'goodbyedpi':UserConfig(CONFIG_PATH+"/goodbyedpi/user.json" if\
                                goodbyedpi_config_path == "" or not os.path.exists(goodbyedpi_config_path) else\
                                goodbyedpi_config_path),
        'zapret':UserConfig(CONFIG_PATH+"/zapret/user.json" if\
                            zapret_config_path == "" or not os.path.exists(zapret_config_path) else\
                            zapret_config_path),
        'byedpi':UserConfig(CONFIG_PATH+"/byedpi/user.json" if\
                            byedpi_config_path == "" or not os.path.exists(byedpi_config_path) else\
                            byedpi_config_path),
        'spoofdpi':UserConfig(CONFIG_PATH+"/spoofdpi/user.json" if\
                            spoofdpi_config_path == "" or not os.path.exists(spoofdpi_config_path) else\
                            spoofdpi_config_path)
    }
except:
    error_message = traceback.format_exc()
    logger.raise_critical(error_message)

def get_log_level():
    log_lvl = settings.settings['GLOBAL']["log_level"]
    if log_lvl == 'critical': return logging.CRITICAL
    elif log_lvl == 'error': return logging.ERROR
    else: return logging.DEBUG

try:
    LOG_LEVEL = get_log_level()
except:
    error_message = traceback.format_exc()
    logger.raise_critical(error_message)

logger.create_logs(f"Importing complete without errors.")
logger.cleanup_logs()