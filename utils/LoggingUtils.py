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

import sys
import time
import logging
import os
import json
import logging.config


class LoggingUtils(object):

    def __init__(self) -> None:
        self.configure_logger()
        self.decorative_logger = logging.getLogger('Bittbot_Decorative')
        self.informative_logger = logging.getLogger('Bittbot_Informative')

    def get_decorative_logger(self):
        return self.decorative_logger

    def get_informative_logger(self):
        return self.informative_logger

    def configure_logger(self):
        path = "logger.json"
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = json.load(f)
            logging.config.dictConfig(config)
            logging.raiseExceptions = False
        else:
            logging.basicConfig(level=logging.DEBUG)

    def logging_info(self, message):
        self.informative_logger.info(message)

    def logging_warning(self, message):
        self.informative_logger.warning(message)

    def logging_error(self, message, *args, **kwargs):
        self.informative_logger.error(message, *args, **kwargs)

    def logging_exception(self, message, *args, exc_info=True, **kwargs):
        self.informative_logger.exception(message, *args, exc_info=exc_info, **kwargs)

    def logging_decorative(self, message):
        self.decorative_logger.info(message)

    def logging_bittbot_error(self, message, seconds=0):
        self.logging_line_char('>')
        self.informative_logger.error("ERROR INESPERADO TIPO: {}".format(sys.exc_info()[1]))
        self.informative_logger.error('ERROR AL {}'.format(message))
        if seconds > 0:
            self.decorative_logger.info('ESPERANDO {} SEGUNDOS '.format(seconds))
            time.sleep(seconds)
            self.logging_line_char('>')

    def logging_line_char(self, char):
        self.decorative_logger.info(char * 80)

    def logging_result(self, message):
        self.logging_line_char('-')
        self.informative_logger.info(message)
        self.logging_line_char('-')

    def logging_empty_line(self):
        self.decorative_logger.info("")

    def logging_result_star(self, message):
        self.logging_line_char('*')
        self.informative_logger.info(message)
        self.logging_line_char('*')

    def print_help(self):
        self.informative_logger.info('\n###############################################################')
        self.informative_logger.info('#                                                             #')
        self.informative_logger.info('# OPCIONES DE LA LINEA DE COMANDOS PARA bittbot.py            #')
        self.informative_logger.info('#                                                             #')
        self.informative_logger.info('# -h Help -- Ver las opciones                                 #')
        self.informative_logger.info('# -f Fichero de configuracion  (Ej. best_alts.cfg)            #')
        self.informative_logger.info('# -a Alt escogida para tradear                                #')
        self.informative_logger.info('# -s Saldo Alt escogida a invertir en el total de las Alts    #')
        self.informative_logger.info('# -o Opcion escogida  (Valores de 1 a 4)                      #')
        self.informative_logger.info('# -m Margen de Incremento de la Alt 24h                       #')
        self.informative_logger.info('# -n Margen de Incremento Actual de la Alt                    #')
        self.informative_logger.info('# -b Margen de Beneficio para todas las ALts                  #')
        self.informative_logger.info('# -l Stop Loss                                                #')
        self.informative_logger.info('# -t Numero Maximo de Alts para Tradear (Opciones 3 y 4)      #')
        self.informative_logger.info('# -c Numero de Ciclos del Bot                                 #')
        self.informative_logger.info('# -macd1 Periodo MACD corto (Solo opcion 3)                   #')
        self.informative_logger.info('# -macd2 Periodo MACD largo (Solo opcion 3)                   #')
        self.informative_logger.info('# -macds Periodo de Smoothing MACD (Solo opcion 3)            #')
        self.informative_logger.info('#                                                             #')
        self.informative_logger.info('###############################################################\n')

    def print_init_bot(self):
        self.logging_empty_line()
        self.decorative_logger.info('### INICIANDO BITTBOT ###')
        self.logging_empty_line()
