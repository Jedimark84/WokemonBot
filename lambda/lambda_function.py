import json
import os
import re

import message_functions as msg
import raid_function as raid
import channel_post as chnl
import callback_query as cbk
import reply_to_message as reply
import garbage_collection as gc

from datetime import datetime

import pymysql # Uploaded as an AWS Lambda Layer

ADMIN_CHAT_ID      = os.environ['ADMIN_CHAT_ID']
CHAT_CHANNEL_LINKS = json.loads(os.environ['CHAT_CHANNEL_LINKS'])

def lambda_handler(event, context):

    try:
        
        # If admin tracking is on, send the event to the admin telegram chat
        if os.environ['ADMIN_TRACKING'] == 'On':
            msg.send_message('ADMIN TRACKING: {0}'.format(event), ADMIN_CHAT_ID)
        
        # Has the trigger originated from EventBridge
        if event.get('resources'):
            if 'wokemon-garbage-collection' in event['resources'][0]:
                return gc.garbage_collection()
        
        # Has the trigger originated from SQS
        if event.get('Records'):
            event = event['Records'][0]
            sqs_message_id = event['messageId']
        
        body = json.loads(event['body'])
        
        # Echo the event body so it appears in CloudWatch Logs
        print(json.dumps(body))
        
        if 'callback_query' in body:
            return cbk.callback_query_handler(body['callback_query'])
        
        if 'channel_post' in body:
            return chnl.channel_post_handler(body['channel_post'])
            
        if 'edited_message' in body:
            return
        
        if 'message' in body:
            
            message = body['message']
            
            # Do not respond to unsupported events
            UNSUPPORTED_EVENTS = ['photo', 'document', 'voice', 'audio', 'forward_from', 'edited_message', 'new_chat_participant', 'left_chat_participant']
            if (any(x in message for x in UNSUPPORTED_EVENTS)):
                return
            
            if 'reply_to_message' in message:
                return reply.reply_to_message_handler(message)
            
            if 'text' in message:
                message_id = message['message_id']
                text       = message['text'].strip()
                chat       = message['chat']
                chat_id    = chat['id']
                
                if 'from' in message:
                    from_obj = message['from']
                    from_id = from_obj['id']
                    from_username = raid.get_username(from_obj)
                else:
                    msg.send_message('Received a message with no from: {0}'.format(body), ADMIN_CHAT_ID)
                    return
                
                if re.match('^/[a-z0-9]+($|\s)', text):
                    
                    bot_command=re.match('^/[a-z0-9]+($|\s)', text)[0].strip()
                    bot_command_params=text.replace(bot_command, '').strip()
                    
                    if bot_command == '/newraid':
                        bot_command_newraid(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/raid':
                        bot_command_raid(bot_command_params, chat_id)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/nickname':
                        bot_command_nickname(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/level':
                        bot_command_level(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/team':
                        bot_command_team(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    else:
                        return
                
                return
        
        msg.send_message('Unrecognised event received with body: {0}'.format(body), ADMIN_CHAT_ID)
    
    except pymysql.err.ProgrammingError as pe:
        msg.send_message('A database error of type {0} has occured: {1}'.format(type(pe), pe.args), ADMIN_CHAT_ID)
        msg.send_message('*\[ERROR\]* A database error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
    
    except Exception as e:
        msg.send_message('An unhandled error of type {0} has occured: {1}\n\n{2}'.format(type(e), e.args, event), ADMIN_CHAT_ID)
        msg.send_message('*\[ERROR\]* An unhandled error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
    
    finally:
        return {
            'statusCode': 200,
            'body': json.dumps('Success.')
        }

def bot_command_newraid(raid_params, chat_id, from_id, from_username):
    
    raid_info = raid.create_raid(raid_params, chat_id, from_id, from_username)
    
    if raid_info.get('error'):
        return msg.send_message('⚠️ Invalid newraid command received: {0}\n{1}'.format(raid_params, raid_info.get('error')), chat_id)
    
    bot_command_raid(str(raid_info.get('raid_id')), chat_id)
    
    # If the newraid request originates from a chat with a channel link then cross post the raid message to the channel
    if CHAT_CHANNEL_LINKS.get(str(chat_id)):
        bot_command_raid(str(raid_info.get('raid_id')), CHAT_CHANNEL_LINKS[str(chat_id)])

def bot_command_level(command_params, chat_id, from_id, from_username):
    
    if not str(command_params).isdigit():
        return msg.send_message('⚠️ Invalid level provided. Please try again.', chat_id)
    else:
        level = int(command_params)
        if not 1 <= level <= 40:
            return msg.send_message('⚠️ Level must be between 1 and 40.', chat_id)
        
        try:
            if raid.update_level(from_id, from_username, level):
                    return msg.send_message('👍 Thanks {0}, I have set your level to {1}.'.format(from_username, level), chat_id)
        
        except Exception as e: raise

def bot_command_nickname(command_params, chat_id, from_id, from_username):
    
    if not re.match('^[A-Za-z0-9]{5,32}$', command_params):
        return msg.send_message('⚠️ Invalid nickname provided. Please try again.', chat_id)
    
    try:
        if raid.update_nickname(from_id, from_username, command_params):
            return msg.send_message('👍 Thanks {0}, I have set your nickname to {1}.'.format(from_username, command_params), chat_id)
    
    except pymysql.err.IntegrityError as pe:
        return msg.send_message('⚠️ Sorry, your nickname has already been claimed.', chat_id)
    
    except Exception as e: raise

def bot_command_team(command_params, chat_id, from_id, from_username):
    
    if not re.match('^valor|mystic|instinct$', command_params, re.IGNORECASE):
        return msg.send_message('⚠️ Invalid team name provided. Please specify either Valor, Mystic or Instinct.', chat_id)
    
    try:
        if raid.update_team(from_id, from_username, command_params):
            return msg.send_message('👍 Thanks {0}, I have set your team to {1}.'.format(from_username, command_params.title()), chat_id)
    
    except Exception as e: raise

# Given a valid raid id number and a chat window:
# This method will return a formatted message displaying the raid details.
# It will also add the sent message id to the tracking table so updates can be sent.
def bot_command_raid(command_params, chat_id):
    
    if not re.match('^\d+$', command_params):
        return msg.send_message('⚠️ That is not a valid raid id.', chat_id)
    
    raid_detail = raid.get_raid_by_id(command_params)
    if not raid_detail:
        return msg.send_message('⚠️ That is not a valid raid id.', chat_id)
    
    tracked_message = msg.send_message(raid.format_raid_message(raid_detail), chat_id, 'MarkdownV2', True)
    
    # Only track messages for raids that have not completed
    if raid_detail['completed'] == 0:
        tracked_data = json.loads(tracked_message.data.decode("utf-8"))
        raid.insert_message_tracking(command_params, tracked_data['result']['chat']['id'], tracked_data['result']['message_id'])
