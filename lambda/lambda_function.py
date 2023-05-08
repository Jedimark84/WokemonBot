import json
import os
import re

import callback_query as cbk
import dynamo_functions as dynamo
import garbage_collection as gc
import message_functions as msg
import raid_function as raid
import reply_to_message as reply

ADMIN_CHAT_ID      = os.environ['ADMIN_CHAT_ID']
CHAT_CHANNEL_LINKS = json.loads(os.environ['CHAT_CHANNEL_LINKS'])

os.environ['TZ'] = 'Europe/London'

client = dynamo.init_boto3_resource()

def lambda_handler(event, context):

    try:
        
        # If admin tracking is on, send the event to the admin telegram chat
        if os.environ['ADMIN_TRACKING'] == 'On':
            msg.send_message('ADMIN TRACKING: {0}'.format(event), ADMIN_CHAT_ID)

        # Has the trigger originated from EventBridge?
        if event.get('resources'):
            if 'wokemon-garbage-collection' in event['resources'][0]:
                return gc.garbage_collection(client)

        # Has the trigger originated from SQS
        if event.get('Records'):
            event = event['Records'][0]
            sqs_message_id = event['messageId']
        
        body = json.loads(event['body'])
        
        # Echo the event body so it appears in CloudWatch Logs
        print(json.dumps(body))
        
        if 'callback_query' in body:
            return cbk.callback_query_handler(body['callback_query'], client)
        
        if 'channel_post' in body:
            return
        #    return chnl.channel_post_handler(body['channel_post'])
            
        if 'edited_message' in body:
            return
        
        if 'message' in body:
            
            message = body['message']
            
            # Do not respond to unsupported events
            UNSUPPORTED_EVENTS = ['photo', 'document', 'voice', 'audio', \
                'forward_from', 'edited_message', 'new_chat_participant', \
                'left_chat_participant', 'edited_channel_post', \
                'my_chat_member'
            ]
            if (any(x in message for x in UNSUPPORTED_EVENTS)):
                return
            
            if 'reply_to_message' in message:
                return reply.reply_to_message_handler(message, client)
            
            if 'text' in message:
                message_id = message['message_id']
                text       = message['text'].strip()
                chat       = message['chat']
                chat_id    = chat['id']
                
                if 'from' in message:
                    from_obj = message['from']
                    from_id = from_obj['id']
                    from_username = get_username(from_obj)
                else:
                    msg.send_message('Received a message with no from: {0}'.format(body), ADMIN_CHAT_ID)
                    return
                
                # Is this slowing the function down?
                #dynamo.update_item('wokemon_users', 'telegram_id', from_id, 'telegram_username', from_username, client)
                
                if re.match('^/[a-z0-9]+($|\s)', text):
                    
                    bot_command=re.match('^/[a-z0-9]+($|\s)', text)[0].strip()
                    bot_command_params=text.replace(bot_command, '').strip()
                    
                    if bot_command == '/newraid':
                        bot_command_newraid(bot_command_params, chat_id, from_id, from_username, client)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/raid':
                        bot_command_raid(bot_command_params, chat_id, client)
                        msg.delete_message(chat_id, message_id)
                    
                    if bot_command == '/nickname':
                        bot_command_nickname(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/level':
                        bot_command_level(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    elif bot_command == '/team':
                        bot_command_team(bot_command_params, chat_id, from_id, from_username)
                        msg.delete_message(chat_id, message_id)
                    
                    #elif bot_command == '/2021':
                    #    if chat['type'] == 'private':
                    #        bot_command_2021(bot_command_params, chat_id, from_id, from_username)
                    #        msg.delete_message(chat_id, message_id)
                    
                    else:
                        return
                
                return
        
        msg.send_message('Unrecognised event received with body: {0}'.format(body), ADMIN_CHAT_ID)
    
    except Exception as e:
        msg.send_message('An unhandled error of type {0} has occured: {1}\n\n{2}'.format(type(e), e.args, event), ADMIN_CHAT_ID)
        msg.send_message('*\[ERROR\]* An unhandled error has occured\. Please try again in a few minutes\.', chat_id, 'MarkdownV2')
    
    finally:
        return {
            'statusCode': 200,
            'body': json.dumps('Success.')
        }

def bot_command_newraid(raid_params, chat_id, from_id, from_username, client):
    
    raid_info = raid.create_raid(raid_params, chat_id, from_id, from_username, client)
    
    if raid_info.get('error'):
        return msg.send_message('⚠️ Invalid newraid command received: {0}\n{1}'.format(raid_params, raid_info.get('error')), chat_id)
    
    bot_command_raid(str(raid_info.get('raid_id')), chat_id, client)
    
    # If the newraid request originates from a chat with a channel link then cross post the raid message to the channel
    if CHAT_CHANNEL_LINKS.get(str(chat_id)):
        bot_command_raid(str(raid_info.get('raid_id')), CHAT_CHANNEL_LINKS[str(chat_id)], client)

# Given a valid raid id number and a chat window:
# This method will return a formatted message displaying the raid details.
# It will also add the sent message id to the tracking table so updates can be sent.
def bot_command_raid(command_params, chat_id, client):
    
    if not re.match('^\d+$', command_params):
        return msg.send_message('⚠️ That is not a valid raid id.', chat_id)
    
    raid_dict = raid.get_raid_by_id(command_params, client)
    if not raid_dict:
        return msg.send_message('⚠️ Raid with raid_id={0} not found.'.format(command_params), chat_id)
    
    tracked_message = msg.send_message(raid.format_raid_message(raid_dict, client), chat_id, 'MarkdownV2', True)
    
    # I only track active raids (i.e. not cancelled or completed)
    if not (any(x in raid_dict for x in ['cancelled', 'completed'])):
        tracked_data = json.loads(tracked_message.data.decode("utf-8"))
        raid.insert_message_tracking(command_params, tracked_data['result']['chat']['id'], tracked_data['result']['message_id'], client)

def get_username(input_json):
    # Some people haven't set a username, so use first_name instead
    if 'username' in input_json:
        from_username = input_json['username']
    else:
        from_username = input_json['first_name']

    return from_username

def bot_command_nickname(command_params, chat_id, from_id, from_username):
    
    if not re.match('^[A-Za-z0-9]{5,32}$', command_params):
        return msg.send_message('⚠️ Invalid nickname provided. Please try again.', chat_id)
    
    try:
        if dynamo.update_item('wokemon_users', 'telegram_id', from_id, 'trainer_name', command_params, client):
            return msg.send_message('👍 Thanks {0}, I have set your nickname to {1}.'.format(from_username, command_params), chat_id)
    
    #Can we check if username has already been claimed....
    
    except Exception as e: raise

def bot_command_team(command_params, chat_id, from_id, from_username):
    
    if not re.match('^valor|mystic|instinct$', command_params, re.IGNORECASE):
        return msg.send_message('⚠️ Invalid team name provided. Please specify either Valor, Mystic or Instinct.', chat_id)
    
    try:
        if dynamo.update_item('wokemon_users', 'telegram_id', from_id, 'trainer_team', command_params.title(), client):
            return msg.send_message('👍 Thanks {0}, I have set your team to {1}.'.format(from_username, command_params.title()), chat_id)
    
    except Exception as e: raise

def bot_command_level(command_params, chat_id, from_id, from_username):
    
    if not str(command_params).isdigit():
        return msg.send_message('⚠️ Invalid level provided. Please try again.', chat_id)
    else:
        level = int(command_params)
        if not 1 <= level <= 50:
            return msg.send_message('⚠️ Level must be between 1 and 50.', chat_id)
        
        try:
            if dynamo.update_item('wokemon_users', 'telegram_id', from_id, 'trainer_level', level, client):
                if level == 50:
                    msg.send_message('https://i.imgur.com/k0ITLxn.mp4', chat_id, disable_web_page_preview='false')
                    return msg.send_message('👏 Congratulations {0} on reaching Level {1}!'.format(from_username, level), chat_id)
                else:
                    return msg.send_message('👍 Thanks {0}, I have set your level to {1}.'.format(from_username, level), chat_id)
        
        except Exception as e: raise
