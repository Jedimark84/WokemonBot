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
    
    callback_query_id = body['callback_query']['id']
    # TODO: Figure out how to respond to callback_query
    answer_callback_query(callback_query_id)
        
def bot_command_newraid(raid_params, chat_id):

    raid_info = raid.create_raid(raid_params, chat_id)
    
    if raid_info.get('error'):
        send_message('ERROR: {0}'.format(raid_info.get('error')), chat_id, None)
    else:
        send_message('Raid created: {0}'.format(raid_info), chat_id, None)
        
def bot_command_listraids(chat_id):
    
    raid_list = raid.list_raids()
    
    if not raid_list:
        send_message('There are no raids currently scheduled.', chat_id)
    else:
        for r in raid_list:
            send_message(raid.format_raid_message(r), chat_id, 'MarkdownV2')
            
def bot_command_raid(command_params, chat_id):
    
    if not re.match('^\d+$', command_params):
        return send_message('That is not a valid raid id.', chat_id, None)
    
    raid_detail = raid.get_raid_by_id(command_params)
    if not raid_detail:
        return send_message('That is not a valid raid id.', chat_id, None)
        
    send_message(raid.format_raid_message(raid_detail), chat_id, 'MarkdownV2', True)

def send_message(text, chat_id, parse_mode=None, send_keyboard=None):
    
    url = URL + "sendMessage?text={0}&chat_id={1}&parse_mode={2}".format(text, chat_id, parse_mode)
    
    if send_keyboard:
        url += '&reply_markup={"inline_keyboard":[[{"text":"Physical","callback_data":"Physical"},{"text":"Remote","callback_data":"Remote"},{"text":"Invite","callback_data":"Invite"}]]}'
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)

def answer_callback_query(callback_query_id):
    
    url = URL + "answerCallbackQuery?callback_query_id={0}".format(callback_query_id)

    http = urllib3.PoolManager()
    resp = http.request('GET', url)