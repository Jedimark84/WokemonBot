import json
import os
import re
import urllib3 # Useful page: http://zetcode.com/python/urllib3/

import raid_function as raid
import database_connection as db
from datetime import datetime

# ARNs can be found at the following: https://github.com/keithrozario/Klayers/blob/master/deployments/python3.8/arns/eu-west-2.csv
# Import pymysql 0.10.0 from layer: arn:aws:lambda:eu-west-2:770693421928:layer:Klayers-python38-PyMySQL:2
# Is this a trusted source? Maybe we should create our own pymysql layer to use. Or bundle with lambda function.
import pymysql

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID  = os.environ['ADMIN_CHAT_ID']
URL            = "https://api.telegram.org/bot{}/".format(TELEGRAM_TOKEN)

def lambda_handler(event, context):
    
    # Write the event out so it appears in the CloudWatch Logs for debugging
    print(event)

    try:
        body = json.loads(event['body'])
        
        if 'callback_query' in body:
            callback_query_handler(body)
            return
            
        chat_id = body['message']['chat']['id']
        text = body['message']['text'].strip()
        
        if re.match('^/[a-z0-9]+($|\s)', text):
            bot_command=re.match('^/[a-z0-9]+($|\s)', text)[0].strip()
            bot_command_params=text.replace(bot_command,'').strip()
            
            if bot_command=='/listraids':
                bot_command_listraids(chat_id)
            elif bot_command=='/newraid':
                bot_command_newraid(bot_command_params, chat_id)
            elif bot_command=='/raid':
                bot_command_raid(bot_command_params, chat_id)
            else:
                send_message('Unsupported Bot Command: {0}\nParams: {1}'.format(bot_command, bot_command_params), chat_id)
        
        else:
            send_message('{0}'.format(body), chat_id)
            
    except pymysql.err.ProgrammingError as pe:
        send_message('*\[ERROR\]* A database error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
        send_message('A database error of type {0} has occured: {1}'.format(type(pe), pe.args), ADMIN_CHAT_ID, None)
        
    except Exception as e:
        send_message('*\[ERROR\]* An unhandled error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
        send_message('An unhandled error of type {0} has occured: {1}'.format(type(e), e.args), ADMIN_CHAT_ID, None)
    
    finally:
        return {
            'statusCode': 200,
            'body': json.dumps('Success.')
        }

def callback_query_handler(body):
    
    try:
        callback_query_id      = body['callback_query']['id']
        callback_query_from    = body['callback_query']['from']
        callback_query_message = body['callback_query']['message']
        callback_query_data    = body['callback_query']['data']
        
        # Validate callback_query_data is a digit
        if not callback_query_data.isdigit():
            return send_message('Received invalid callback_query_data: {0}'.format(callback_query_data), ADMIN_CHAT_ID, None)
        
        user_id = callback_query_from['id']
        chat_id = callback_query_message['chat']['id']
        
        msg_txt = callback_query_message["text"].split(';')[0]
        
        if re.match('^Raid\s(\d)+$', msg_txt):
            raid_id = msg_txt.split(' ')[1]

            if raid.join_raid(callback_query_from, raid_id, callback_query_data):
                send_message('{0}'.format('something changed'), chat_id, None)
                # Now need to update every message that has referenced this raid and update it
                # TODO - UP TO HERE
            #else:
            #    send_message('{0}'.format('nothing changed'), chat_id, None)
        else:
            send_message('An unrecognised callback query was received: {0}'.format(body), ADMIN_CHAT_ID, None)
    
    except Exception as e:
        send_message('*\[ERROR\]* An unhandled error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
        send_message('An unhandled error of type {0} has occured: {1}'.format(type(e), e.args), ADMIN_CHAT_ID, None)
        
    finally:
        answer_callback_query(callback_query_id)
        
def bot_command_newraid(raid_params, chat_id):

    raid_info = raid.create_raid(raid_params, chat_id)
    
    if raid_info.get('error'):
        return send_message('ERROR: {0}'.format(raid_info.get('error')), chat_id, None)
    
    bot_command_raid(str(raid_info.get('raid_id')), chat_id)
        
def bot_command_listraids(chat_id):
    
    raid_list = raid.list_raids()
    
    if not raid_list:
        send_message('There are no raids currently scheduled.', chat_id)
    else:
        for r in raid_list:
            send_message(raid.format_raid_message(r), chat_id, 'MarkdownV2')

# Given a valid raid id number and a chat window:
# This method will return a formatted message displaying the raid details.
# It will also add the sent message id to the tracking table so updates can be sent.
def bot_command_raid(command_params, chat_id):
    
    if not re.match('^\d+$', command_params):
        return send_message('That is not a valid raid id.', chat_id, None)
    
    raid_detail = raid.get_raid_by_id(command_params)
    if not raid_detail:
        return send_message('That is not a valid raid id.', chat_id, None)
        
    tracked_message = send_message(raid.format_raid_message(raid_detail), chat_id, 'MarkdownV2', True)
    tracked_data = json.loads(tracked_message.data.decode("utf-8"))
    raid.insert_message_tracking(command_params, tracked_data['result']['chat']['id'], tracked_data['result']['message_id'])

def send_message(text, chat_id, parse_mode=None, send_keyboard=None):
    
    url = URL + "sendMessage?text={0}&chat_id={1}&parse_mode={2}".format(text, chat_id, parse_mode)
    
    if send_keyboard:
        url += '&reply_markup={"inline_keyboard":[[{"text":"Physical","callback_data":1}, \
        {"text":"Remote","callback_data":2},{"text":"Invite","callback_data":3}]]}'
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    
    return resp

def answer_callback_query(callback_query_id):
    
    url = URL + "answerCallbackQuery?callback_query_id={0}".format(callback_query_id)

    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    
def edit_message(chat_id, message_id, text, parse_mode=None, send_keyboard=None):
    
    url = URL + "editMessageText?chat_id={0}&message_id={1}&text={2}&parse_mode={3}".format(chat_id, message_id, text, parse_mode)
    
    if send_keyboard:
        url += '&reply_markup={"inline_keyboard":[[{"text":"Physical","callback_data":1}, \
        {"text":"Remote","callback_data":2},{"text":"Invite","callback_data":3}]]}'
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)