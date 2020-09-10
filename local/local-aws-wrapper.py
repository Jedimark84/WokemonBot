# -*- coding: UTF8 -*-
import json
from pprint import pprint

import requests

from lambda_function import lambda_handler


class BotHandler:
    def __init__(self, token):
            self.token = token
            self.api_url = "https://api.telegram.org/bot{}/".format(token)

    #url = "https://api.telegram.org/bot<token>/"

    def get_updates(self, offset=0, timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params)
        return resp

    def get_first_update(self):
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result[0]
        else:
            last_update = None

        return last_update


token = '946135256:AAFv4KUOwNR4lDGJbjw9f_SjCSM202VtOCg' #Token of your bot
wokemon_bot = BotHandler(token) #Your bot's name



def main():
    new_offset = 0

    while True:
        all_updates=wokemon_bot.get_updates(new_offset)

        if len(all_updates) > 0:
            for current_update in all_updates:
                pprint(current_update)
                first_update_id = current_update['update_id']

                lambda_handler(wrap_for_lambda(current_update), "")
                new_offset = first_update_id + 1


# AWS lambda receives the updates wrapped up. We only make use of a small part of those
# so we simply wrap the JSON from the raw telegram API up in the same structure
# that the bot will receive when running on AWS.
def wrap_for_lambda(input_message):
    data_set = {"body": json.dumps(input_message)}
    pprint(data_set)
    return data_set


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit()