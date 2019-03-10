#  This file is part of Bittbot.
#
#  Bittbot is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Bittbot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Bittbot. If not, see <https://www.gnu.org/licenses/>.

import json
import sys

from pathlib import Path
from domain import Parameters
from domain import InfoAlt
from utils.LoggingUtils import LoggingUtils

VERSION_MAJOR = 2
VERSION_MINOR = 1
VERSION_REVISION = 2

API_KEYS_GENERATOR = "A"
CONFIG_GENERATOR = "B"
CONFIG_TELEGRAM = "C"
STRATEGY_MANUAL_INCREMENT_24H_ALL_ALTS = "1"
STRATEGY_BBANDS = "2"
STRATEGY_MACD_RSI = "3"
STRATEGY_AUTO_MARGIN = "4"

API_KEYS_FILE = "apikeys.cfg"
TELEGRAM_CONFIG_FILE = "telegram.cfg"

logger = LoggingUtils()


def read_config(fichero):
    try:
        config_file = Path(fichero)
        if not config_file.is_file():
            logger.logging_error("Config file missing: {}", fichero)
            sys.exit(0)
        with open(fichero, 'r') as config_file:
            data = json.load(config_file)
            data["WorkingAlts"] = data["Coins"]
            return data
    except Exception:
        logger.logging_bittbot_error("ABRIR FICHERO DE CONFIGURACION : {}".format(fichero))
        sys.exit(1)


def read_api_keys_config():
    try:
        config_file = Path(API_KEYS_FILE)
        if not config_file.is_file():
            generate_empty_api_key_file()
            ask_user_api_keys()
        with open(API_KEYS_FILE, 'r') as config_file:
            apikeys = json.load(config_file)
            # Trim spaces
            for key, value in apikeys.items():
                apikeys[key] = value.strip()
            return apikeys
    except Exception:
        logger.logging_bittbot_error("ABRIR FICHERO DE API KEYS")
        sys.exit(1)


def generate_empty_api_key_file():
    contents = {"Bittrex_ApiKey": "", "Bittrex_ApiSecret": "", "Poloniex_ApiKey": "", "Poloniex_ApiSecret": ""}
    with open(API_KEYS_FILE, 'w') as outfile:
        json.dump(contents, outfile, indent=4)


def ask_user_api_keys():
    with open(API_KEYS_FILE, 'r') as config_file:
        current_config = json.load(config_file)

    exchange = ""
    while exchange != "Bittrex" and exchange != "Poloniex":
        exchange = input('Introduce el exchange (Poloniex o Bittrex): ')
    api_key = input('Introduce tu Api Key: ').strip()
    api_secret = input('Introduce tu Api Secret: ').strip()

    contents = {}
    contents["Bittrex_ApiKey"] = api_key if exchange == "Bittrex" else current_config["Bittrex_ApiKey"]
    contents["Bittrex_ApiSecret"] = api_secret if exchange == "Bittrex" else current_config["Bittrex_ApiSecret"]
    contents["Poloniex_ApiKey"] = api_key if exchange == "Poloniex" else current_config["Poloniex_ApiKey"]
    contents["Poloniex_ApiSecret"] = api_secret if exchange == "Poloniex" else current_config["Poloniex_ApiSecret"]
    with open(API_KEYS_FILE, 'w') as outfile:
        json.dump(contents, outfile, indent=4)


def read_telegram_config():
    try:
        config_file = Path(TELEGRAM_CONFIG_FILE)
        if config_file.is_file():
            with open(TELEGRAM_CONFIG_FILE, 'r') as config_file:
                return json.load(config_file)
        return None
    except Exception:
        return None


def is_help_parameter_set():
    pos = get_argument_position(sys.argv, '-h')
    if pos > 0:
        return True
    return False


def get_config_file():
    pos = get_argument_position(sys.argv, '-f')
    if pos > 0:
        file = sys.argv[pos + 1]
        logger.logging_info('CARGANDO FICHERO {} CON LA CONFIGURACION PERSONALIZADA'.format(file))
    else:
        file = 'bittbot.cfg'
        logger.logging_info('CARGANDO FICHERO {} CON LA CONFIGURACION ESTANDAR'.format(file))
    return file


def get_balance_invest(api, alt):
    account_balance = api.get_balance(alt)
    if account_balance is None:
        logger.logging_error('Parece que hay un error en tu combinacion de Api Key y Api Secret. Por favor, revisalos.')
        sys.exit(0)
    logger.logging_decorative('Entra saldo Maximo de {} a invertir. Maximo Disponible: {} {}'.format(alt, account_balance, alt))

    balance_invest = float(get_parameter_value('-s', 'Inversion:? '))
    if get_argument_position(sys.argv, '-bypass_restrictions') > 0:
        return balance_invest
    while balance_invest <= 0.0 or balance_invest > account_balance:
        balance_invest = float(get_parameter_value('-s', 'Inversion:? '))
    return balance_invest


def get_margin_increment_24h():
    margin_increment_24h = get_parameter_value('-m', 'Entra el margen de incremento de las ultimas 24h para entrar a invertir:? ')
    return float(margin_increment_24h) / 100


def get_current_margin_increment():
    current_margin_increment = get_parameter_value('-n', 'Entra el margen de incremento actual de la Alt para entrar a invertir (0% -> 100%):? ')
    return float(current_margin_increment) / 100


def get_profit_margin_alts():
    profit_margin_alts = 0.0
    while profit_margin_alts <= 0.5:
        profit_margin_alts = get_parameter_value('-b', 'Entra el margen de beneficio para todas las Alts: ? ')
        profit_margin_alts = float(profit_margin_alts.replace(',', '.'))
    return profit_margin_alts


def get_strategy_type():
    pos = get_argument_position(sys.argv, '-o')
    if pos > 0:
        return sys.argv[pos + 1]
    return menu_operation_type()


def get_short_macd():
    macd_short_period = get_parameter_value('-macd1', 'Entra el Periodo Corto de MACD (Recomendado 12): ? ')
    return int(macd_short_period)


def get_long_macd():
    macd_long_period = get_parameter_value('-macd2', 'Entra el Periodo Largo de MACD (Recomendado 24): ? ')
    return int(macd_long_period)


def get_macd_smoothing():
    macd_smoothing = get_parameter_value('-macds', 'Entra el Periodo de smoothing para MACD (Recomendado 9): ? ')
    return int(macd_smoothing)


def get_stop_loss():
    stop_loss = get_parameter_value('-l', 'Entra el margen de perdidas aceptado (0 no se utiliza):? ')
    return float(stop_loss) / 100


def get_max_alts_to_trade(max_alts):
    max_alts_to_trade = 0
    while max_alts_to_trade < 1 or max_alts_to_trade > max_alts:
        max_alts_to_trade = int(get_parameter_value('-t', 'Entra el Num. Max de Alts a tradear: (1 - {})? '.format(max_alts)))
    return max_alts_to_trade


def get_cycles():
    cycles = 0
    while cycles < 1:
        cycles = int(get_parameter_value('-c', 'Numero de ciclos total entre todas las Alts para la Inversion:? '))
    return cycles


def get_bbands_crossing_share():
    bbands_crossing_share = get_parameter_value('-bbcs', 'Entra el margen minimo de cruce para la Banda suelo de Bollinger Bands (0% -> 100%):? ')
    return float(bbands_crossing_share) / 100


def get_market_state_24h_share():
    market_state_24h_share = get_parameter_value('-bbms24', 'Entra el margen de incremento del mercado deseado en 24 horas (0% -> 100%):? ')
    return float(market_state_24h_share) / 100


def get_market_state_12h_share():
    market_state_12h_share = get_parameter_value('-bbms12', 'Entra el margen de incremento del mercado deseado en 12 horas (0% -> 100%):? ')
    return float(market_state_12h_share) / 100


def get_market_state_5h_share():
    market_state_5h_share = get_parameter_value('-bbms5', 'Entra el margen de incremento del mercado deseado en 5 horas (0% -> 100%):? ')
    return float(market_state_5h_share) / 100


def get_coin_selection_min_volume():
    coin_selection_min_volume = get_parameter_value('-bbvol', 'Entra el volumen minimo para seleccionar una Alt (400):? ')
    return int(coin_selection_min_volume)


def get_coin_selection_min_24_increment():
    coin_selection_min_24_increment = get_parameter_value('-bbmin24', 'Entra el margen de incremento mínimo de la Alt para entrar a invertir (0% -> 100%):? ')
    return float(coin_selection_min_24_increment)


def get_coin_selection_max_24_increment():
    coin_selection_max_24_increment = get_parameter_value('-bbmax24', 'Entra el margen de incremento máximo de la Alt para entrar a invertir (0% -> 100%):? ')
    return float(coin_selection_max_24_increment)


# Populates coins_trader from working_alts
def populate_coins(params: Parameters):
    pos = 0
    for coin_name in params.working_alts:
        fit_coin = InfoAlt.InfoAlt()
        fit_coin.posicion = pos
        fit_coin.n_alt = params.altstr + '_' + coin_name
        params.coins_trader.append(fit_coin)
        pos += 1


######################
# Auxiliar functions #
######################
def get_argument_position(arguments, search_argument):
    n = 0
    for argument in arguments:
        if argument == search_argument:
            return n
        else:
            n += 1
    return -1


def get_parameter_value(arg_name, ask_phrase):
    pos = get_argument_position(sys.argv, arg_name)
    if pos > 0:
        value = sys.argv[pos + 1]
    else:
        value = input(ask_phrase).strip()
    return value


def menu_operation_type():
    program_type = ""
    while program_type != API_KEYS_GENERATOR and program_type != CONFIG_GENERATOR and program_type != STRATEGY_AUTO_MARGIN \
            and program_type != STRATEGY_MACD_RSI and program_type != STRATEGY_BBANDS \
            and program_type != STRATEGY_MANUAL_INCREMENT_24H_ALL_ALTS and program_type != CONFIG_TELEGRAM:
        logger.logging_empty_line()
        logger.logging_decorative('Escoge el modo como operara BittBot')
        logger.logging_decorative('    {}-> Añadir / Modificar API KEYs'.format(API_KEYS_GENERATOR))
        logger.logging_decorative('    {}-> Generador de ficheros de configuración'.format(CONFIG_GENERATOR))
        logger.logging_decorative('    {}-> Configuración del bot de Telegram'.format(CONFIG_TELEGRAM))
        logger.logging_decorative('-----------------------------------------------------------------------------------------')
        logger.logging_decorative('    {}-> Segun Margen de Incremento 24h (Con todas las Alts)'.format(STRATEGY_MANUAL_INCREMENT_24H_ALL_ALTS))
        logger.logging_decorative('    {}-> Análisis técnico (Bollinger Bands)'.format(STRATEGY_BBANDS))
        logger.logging_decorative('    {}-> Análisis técnico (MACD + RSI)'.format(STRATEGY_MACD_RSI))
        logger.logging_decorative('    {}-> Automatico. Escoge las mejores Alts para tradear en cada momento (Segun Margenes)'.format(STRATEGY_AUTO_MARGIN))
        logger.logging_empty_line()
        program_type = input('Opcion: ? ')
    return program_type

