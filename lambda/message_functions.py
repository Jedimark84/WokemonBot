import urllib3
import json
import os

from urllib.parse import quote

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
API_URL        = "https://api.telegram.org/bot{0}/".format(TELEGRAM_TOKEN)
RAID_KEYBOARD  = '&reply_markup={"inline_keyboard":[[ {"text":"✅️","callback_data":1},  \
                                                     {"text":"📍","callback_data":2},  \
                                                     {"text":"📩","callback_data":3},  \
                                                     {"text":"🚫","callback_data":4},  \
                                                     {"text":"➕","callback_data":0}]]}'

RAID_KEYBOARD2 = '&reply_markup={"inline_keyboard":[[ {"text":"✅️","callback_data":1},  \
                                                     {"text":"🚫","callback_data":4},  \
                                                     {"text":"➕","callback_data":0}]]}'

def send_message(text: str, chat_id: int, parse_mode: str=None, send_keyboard: bool=False, disable_web_page_preview: str='true') -> urllib3.HTTPResponse:

    if text.endswith('RAID COMPLETED'):
        text = text.replace('RAID COMPLETED','')
        send_keyboard = False
    
    url = ''.join([API_URL, 'sendMessage?disable_web_page_preview={0}&text={1}&chat_id={2}'.format(disable_web_page_preview, quote(text), chat_id)])
    url = ''.join([url, '' if not parse_mode else '&parse_mode={0}'.format(parse_mode)])
    
    if send_keyboard and not 'RAID CANCELLED' in text:
        if 'The Remote Lobby is Full' in text:
            url += RAID_KEYBOARD2
        else:
            url += RAID_KEYBOARD
    
    return http_get(url)

def answer_callback_query(callback_query_id: int) -> urllib3.HTTPResponse:
    
    url = ''.join([API_URL, 'answerCallbackQuery?callback_query_id={0}'.format(callback_query_id)])
    
    return http_get(url)

def edit_message(chat_id, message_id, text, parse_mode=None, send_keyboard=None):
    
    if text.endswith('RAID COMPLETED'):
        text = text.replace('RAID COMPLETED','')
        send_keyboard = False
    
    url = ''.join([API_URL, 'editMessageText?disable_web_page_preview=true&chat_id={0}&message_id={1}&text={2}'.format(chat_id, message_id, quote(text))])
    url = ''.join([url, '' if not parse_mode else '&parse_mode={0}'.format(parse_mode)])
    
    if send_keyboard and not 'RAID CANCELLED' in text:
        if 'The Remote Lobby is Full' in text:
            url += RAID_KEYBOARD2
        else:
            url += RAID_KEYBOARD
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)

def delete_message(chat_id: int, message_id: int):
    
    url = ''.join([API_URL, 'deleteMessage?chat_id={0}&message_id={1}'.format(chat_id, message_id)])
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)

def getChat(chat_id: int) -> dict():
    
    url = ''.join([API_URL, 'getChat?chat_id={0}'.format(chat_id)])
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    
    return decode_http_response_as_dict(resp)

# Perform a http GET request and return the response
def http_get(url: str) -> urllib3.HTTPResponse:
    
    http = urllib3.PoolManager()
    return http.request('GET', url)

# Decode a HTTPResponse and return as a dict
def decode_http_response_as_dict(http_response: urllib3.HTTPResponse) -> dict():
    
    return json.loads(http_response.data.decode("utf-8"))
