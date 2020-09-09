import json
import os
import re
import urllib3

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
        
        #send_message('ADMIN TRACKING: {0}'.format(body), 581975002)
        
        if 'callback_query' in body:
            callback_query = body['callback_query']
            callback_query_handler(callback_query)
            return
        
        if 'message' in body:
            message = body['message']
            chat = message['chat']
            
            if 'reply_to_message' in message:
                #reply_to_message = message['reply_to_message']
                reply_to_message_handler(message)
                return
            
            if 'new_chat_participant' in message:
                new_chat_participant = message['new_chat_participant']
                send_message('new_chat_participant message received: {0}'.format(body), ADMIN_CHAT_ID, None)
                return
            
            if 'left_chat_participant' in message:
                left_chat_participant = message['left_chat_participant']
                send_message('left_chat_participant message received: {0}'.format(body), ADMIN_CHAT_ID, None)
                return
            
            if 'text' in message:
                text = message['text'].strip()
                
                chat_id = chat['id']
                
                if 'from' in message:
                    from_obj = message['from']
                    from_id = from_obj['id']
                    
                    # Some people haven't set a username, so use first_name instead
                    if 'username' in from_obj:
                        from_username = from_obj['username']
                    else:
                        from_username = from_obj['first_name']
                else:
                    send_message('Received a message with no from: {0}'.format(body), ADMIN_CHAT_ID)
                    return
                
                if re.match('^/[a-z0-9]+($|\s)', text):
                    
                    bot_command=re.match('^/[a-z0-9]+($|\s)', text)[0].strip()
                    bot_command_params=text.replace(bot_command,'').strip()
                    
                    if bot_command == '/newraid':
                        bot_command_newraid(bot_command_params, chat_id, from_id, from_username)
                    
                    elif bot_command == '/raid':
                        bot_command_raid(bot_command_params, chat_id)
                    
                    elif bot_command == '/nickname':
                        bot_command_nickname(bot_command_params, chat_id, from_id, from_username)
                    
                    elif bot_command == '/level':
                        bot_command_level(bot_command_params, chat_id, from_id, from_username)
                    
                    elif bot_command == '/team':
                        bot_command_team(bot_command_params, chat_id, from_id, from_username)
                    
                    #elif bot_command == '/listraids':
                    #    bot_command_listraids(chat_id)
                    
                    else:
                        return
                    #    send_message('Unsupported Bot Command: {0}\nParams: {1}'.format(bot_command, bot_command_params), chat_id)
                #else:
                #    send_message('{0}'.format(message), chat_id)
                
                return
        
        send_message('Unsupported event received with body: {0}'.format(body), ADMIN_CHAT_ID, None)
    
    except pymysql.err.ProgrammingError as pe:
        send_message('*\[ERROR\]* A database error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
        send_message('A database error of type {0} has occured: {1}'.format(type(pe), pe.args), ADMIN_CHAT_ID, None)
    
    except Exception as e:
        send_message('*\[ERROR\]* An unhandled error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
        send_message('An unhandled error of type {0} has occured: {1}\n\n{2}'.format(type(e), e.args, body), ADMIN_CHAT_ID, None)
    
    finally:
        return {
            'statusCode': 200,
            'body': json.dumps('Success.')
        }

def reply_to_message_handler(message):
    
    message_id = message['message_id']
    quoted_message_text = message['reply_to_message']['text']
    reply_text = message['text']
    chat_id = message['chat']['id']
    
    text_split = quoted_message_text.split(';')[0]
    
    if re.match('^Raid\s(\d)+$', text_split):
        raid_id = text_split.split(' ')[1]
        
        from_obj = message['from']
        from_id = from_obj['id']
        
        # Some people haven't set a username, so use first_name instead
        if 'username' in from_obj:
            from_username = from_obj['username']
        else:
            from_username = from_obj['first_name']
        
        if reply_text == '/cancel':
            response = raid.cancel_raid(raid_id, from_id)
            
            if response.get('success'):
                formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                tracking = raid.get_message_tracking_by_id(raid_id)
                for t in tracking:
                    edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                return send_message('Raid Cancelled.', chat_id, None)
            else:
                return send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)
        
        if reply_text.startswith('/time'):
            if not re.match('^/time\s([01]?[0-9]|2[0-3]):[0-5][0-9]$', reply_text):
                return send_message('ERROR: Please supply the time in the format: hh:mm', chat_id, None)
            else:
                time = reply_text.replace('/time', '').strip()
                response = raid.change_raid_time(raid_id, from_id, time)
                if response.get('success'):
                    raid.insert_raid_comment('Changed the raid time to {0}'.format(time), from_username, raid_id, message_id)
                    formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                    tracking = raid.get_message_tracking_by_id(raid_id)
                    for t in tracking:
                        edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                    return send_message('Raid time has been changed.', chat_id, None)
                else:
                    return send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)
        
        if reply_text.startswith('/title'):
            title = reply_text.replace('/title','').strip()[:50].strip()
            response = raid.change_raid_title(raid_id, from_id, title)
            if response.get('success'):
                raid.insert_raid_comment('Changed the raid title to {0}'.format(title), from_username, raid_id, message_id)
                formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                tracking = raid.get_message_tracking_by_id(raid_id)
                for t in tracking:
                    edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                return send_message('Raid title has been changed.', chat_id, None)
            else:
                return send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)
        
        if reply_text.startswith('/location'):
            location = reply_text.replace('/location','').strip()[:50].strip()
            response = raid.change_raid_location(raid_id, from_id, location)
            if response.get('success'):
                raid.insert_raid_comment('Changed the raid location to {0}'.format(location), from_username, raid_id, message_id)
                formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                tracking = raid.get_message_tracking_by_id(raid_id)
                for t in tracking:
                    edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                return send_message('Raid location has been changed.', chat_id, None)
            else:
                return send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)        
        
        if raid.insert_raid_comment(reply_text.strip()[:200].strip(), from_username, raid_id, message_id):
            formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
            tracking = raid.get_message_tracking_by_id(raid_id)
            for t in tracking:
                edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
    else:
        send_message('Unsupported reply_to_message message received: {0}'.format(message), ADMIN_CHAT_ID, None)
    
    return True

def callback_query_handler(callback_query):
    
    try:
        callback_query_id      = callback_query['id']
        callback_query_from    = callback_query['from']
        callback_query_message = callback_query['message']
        callback_query_data    = callback_query['data']
        
        # Validate callback_query_data is a digit
        if not callback_query_data.isdigit():
            return send_message('Received invalid callback_query_data: {0}'.format(callback_query_data), ADMIN_CHAT_ID, None)
        
        user_id = callback_query_from['id']
        chat_id = callback_query_message['chat']['id']
        
        msg_txt = callback_query_message["text"].split(';')[0]
        
        if re.match('^Raid\s(\d)+$', msg_txt):
            raid_id = msg_txt.split(' ')[1]
            
            if raid.join_raid(callback_query_from, raid_id, callback_query_data):
                formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                tracking = raid.get_message_tracking_by_id(raid_id)
                for t in tracking:
                    edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
        
        else:
            send_message('An unrecognised callback query was received: {0}'.format(callback_query), ADMIN_CHAT_ID, None)
    
    except Exception as e:
        send_message('*\[ERROR\]* An unhandled error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
        send_message('An unhandled error of type {0} has occured: {1}'.format(type(e), e.args), ADMIN_CHAT_ID, None)
    
    finally:
        answer_callback_query(callback_query_id)

def bot_command_newraid(raid_params, chat_id, from_id, from_username):
    
    raid_info = raid.create_raid(raid_params, chat_id, from_id, from_username)
    
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

def bot_command_level(command_params, chat_id, from_id, from_username):
    
    if not str(command_params).isdigit():
        return send_message('ERROR: Invalid level provided. Please try again.', chat_id, None, None)
    else:
        level = int(command_params)
        if not 1 <= level <= 40:
            return send_message('ERROR: Level must be between 1 and 40.', chat_id, None, None)
        
        try:
            if raid.update_level(from_id, from_username, level):
                return send_message('Updated your level.', chat_id, None, None)
        
        except Exception as e: raise

def bot_command_nickname(command_params, chat_id, from_id, from_username):
    
    if not re.match('^[A-Za-z0-9]{5,32}$', command_params):
        return send_message('ERROR: Invalid nickname provided. Please try again.', chat_id, None, None)
    
    try:
        if raid.update_nickname(from_id, from_username, command_params):
            return send_message('Updated your nickname.', chat_id, None, None)
    
    except pymysql.err.IntegrityError as pe:
        return send_message('Sorry, your nickname has already been claimed.', chat_id, None, None)
    
    except Exception as e: raise

def bot_command_team(command_params, chat_id, from_id, from_username):
    
    if not re.match('^valor|mystic|instinct$', command_params, re.IGNORECASE):
        return send_message('ERROR: Invalid team name provided. Please specify either Valor, Mystic or Instinct.', chat_id, None, None)
    
    try:
        if raid.update_team(from_id, from_username, command_params):
            return send_message('Updated your team.', chat_id, None, None)
    
    except Exception as e: raise

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
    
    if send_keyboard and not 'RAID CANCELLED' in text:
        url += '&reply_markup={"inline_keyboard":[[ {"text":"✅️","callback_data":1},  \
                                                    {"text":"📍","callback_data":2},  \
                                                    {"text":"📩","callback_data":3},  \
                                                    {"text":"🚫","callback_data":4},  \
                                                    {"text":"➕","callback_data":0}]]}'
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    
    return resp

def answer_callback_query(callback_query_id):
    
    url = URL + "answerCallbackQuery?callback_query_id={0}".format(callback_query_id)
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)

def edit_message(chat_id, message_id, text, parse_mode=None, send_keyboard=None):
    
    url = URL + "editMessageText?chat_id={0}&message_id={1}&text={2}&parse_mode={3}".format(chat_id, message_id, text, parse_mode)
    
    if send_keyboard and not 'RAID CANCELLED' in text:
        url += '&reply_markup={"inline_keyboard":[[ {"text":"✅️","callback_data":1},  \
                                                    {"text":"📍","callback_data":2},  \
                                                    {"text":"📩","callback_data":3},  \
                                                    {"text":"🚫","callback_data":4},  \
                                                    {"text":"➕","callback_data":0}]]}'
    
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
