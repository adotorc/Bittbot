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

import telebot
import json

from utils import Config


class ConfigTelegram(object):

    def __init__(self):
        self.api_token = ""
        self.user_id = ""
        self.chat_id = ""
        self.bot = None

    def run(self):
        print('')
        print('Bienvenido a la configuración del Bot de Telegram para Bittbot')
        print('A continuación, os guiaremos en el proceso de configuración de Bittbot para ejecutar el bot de Telegram correctamente.')
        self.api_token = self.get_api_token()
        self.bot = telebot.TeleBot(self.api_token)

        @self.bot.message_handler(commands=['start'])
        def handle_start_help(message):
            self.start_command(message)

        print('')
        print('Veréis que en el chat también os especifican la dirección de vuestro BOT, con una dirección del estilo:')
        print('t.me/NOMBRE_DEL_BOT')
        print('')
        print('Abrir la dirección de vuestro bot en Telegram para seguir con la configuración')
        print('Os ejecutara directamente el comando /start cuando habléis por primera vez con vuestro bot')
        print('Si no fuera así, ejecutar "/start" (sin comillas)')
        print('')
        self.bot.polling()

    def start_command(self, message):
        self.user_id = message.from_user.id
        self.chat_id = message.chat.id
        self.generate_config_file()
        self.bot.send_message(self.chat_id, "¡Bot configurado con éxito!")
        self.finish()

    def get_api_token(self):
        print('')
        print('Abrir la siguiente url en Telegram:')
        print('https://telegram.me/botfather')
        print('')
        print('Escribir "/newbot" (sin comillas) en el bot FatherBot que se os ha abierto con el enlace anterior.')
        print('Elegir un nombre para vuestro bot. El único requisito es que dicho nombre debe terminar en "bot"')
        print('Una vez elegido el nombre correctamente el bot os dirá vuestra HTTP Api.')
        print('Copiarla a continuación')
        print('')
        api = ''
        correct = False
        while not correct:
            api = input('Introduce tu HTTP Api: ').strip()
            answer = input('La Api introducida es: ' + api + ". ¿Es correcto? (si/no)")
            correct = answer == "si"
        return api

    def generate_config_file(self):
        new_config = {"Token": self.api_token, "UserId": self.user_id, "ChatId": self.chat_id}
        with open(Config.TELEGRAM_CONFIG_FILE, 'w') as outfile:
            json.dump(new_config, outfile, indent=4)

    def finish(self):
        print('')
        print('¡Bot configurado con éxito!')
        self.bot.stop_polling()
