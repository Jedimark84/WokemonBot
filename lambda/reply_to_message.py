import re
import string

import message_functions as msg
import raid_function as raid

RESPOND_ONLY_TO_IDS = [555076590, 5365883597, 1353986583] # IDs for @Wokemon_bot, @WokemonNoSQL and @Wokedev_bot
SUPPORTED_COMMANDS  = ['cancel', 'time', 'title', 'location']

def reply_to_message_handler(message: dict, client):
    
    try:
        
        # Check all mandatory fields exist in message
        if not (all(x in message for x in ['message_id', 'from', 'chat', 'reply_to_message', 'text'])):
            return
        
        message_id       = message['message_id']
        from_obj         = message['from']
        chat             = message['chat']
        reply_to_message = message['reply_to_message']
        reply_text       = message['text']
        
        # Check all mandatory fields exist in reply_to_message
        if not (all(x in reply_to_message for x in ['message_id', 'from', 'chat', 'text'])):
            return
        
        # I only respond to a reply_to_message if the original message came from me
        if not reply_to_message['from']['id'] in RESPOND_ONLY_TO_IDS:
            return
        
        quoted_message_text = reply_to_message['text']
        text_split          = quoted_message_text.split(';')[0]
        
        # I only respond to raid information messages
        if re.match('^Raid\s(\d)+$', text_split):
            
            raid_id       = int(text_split.split(' ')[1])
            chat_id       = int(chat['id'])
            from_id       = int(from_obj['id'])
            from_username = raid.get_username(from_obj)

            # I only respond to active raids (i.e. not cancelled or completed)
            if (any(x in raid.get_raid_by_id(raid_id, client) for x in ['cancelled', 'completed'])):
                return

            # Is the reply a bot command?
            if reply_text.startswith('/'):
                
                # Get the bot command and check the command is supported
                bot_command = reply_text[1:].split(' ')[0].strip()
                bot_command_params = reply_text[1:].replace(bot_command, '').strip()
                
                if not any(x==bot_command for x in SUPPORTED_COMMANDS):
                    return
                
                if bot_command == 'cancel':
                    return bot_command_cancel(message_id, chat_id, raid_id, from_id, client)
                
                if bot_command == 'time':
                    return bot_command_time(message_id, chat_id, raid_id, from_id, from_username, bot_command_params, client)
                
                if bot_command == 'title':
                    return bot_command_title(message_id, chat_id, raid_id, from_id, from_username, bot_command_params, client)
                
                if bot_command == 'location':
                    return bot_command_location(message_id, chat_id, raid_id, from_id, from_username, bot_command_params, client)
            
            else:
                return leave_comment_and_update_messages(message_id, raid_id, from_username, reply_text, client)
        
        return
    
    except Exception as e: raise

def bot_command_cancel(message_id, chat_id, raid_id, from_id, client):
    
    response = raid.cancel_raid(raid_id, from_id, client)
    if response.get('success'):
        update_tracked_messages(raid_id, client)
        return msg.send_message('❌ Raid {0} has been cancelled.'.format(raid_id), chat_id, None)
    else:
        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def bot_command_time(message_id, chat_id, raid_id, from_id, from_username, time_param, client):
    
    if not re.match('^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_param):
        return msg.send_message('ERROR: Please supply the time in the format: hh:mm', chat_id, None)
    
    else:
        response = raid.update_raid_time(raid_id, from_id, time_param, client)
        print("Got response: {0}".format(response))
        
        if response.get('success'):
            leave_comment_and_update_messages(message_id, raid_id, from_username, 'Updated the raid time to {0}'.format(time_param), client)
            return msg.send_message(response.get('success'), chat_id, None)
        
        else:
            return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def bot_command_title(message_id, chat_id, raid_id, from_id, from_username, title_param, client):
    
    title = string.capwords(title_param[:50].strip())
    response = raid.update_raid_title(raid_id, from_id, title, client)
    
    if response.get('success'):
        leave_comment_and_update_messages(message_id, raid_id, from_username, 'Updated the raid title to {0}'.format(title_param), client)
        return msg.send_message(response.get('success'), chat_id, None)
    
    else:
        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def bot_command_location(message_id, chat_id, raid_id, from_id, from_username, location_param, client):
    
    location = string.capwords(location_param[:50].strip())
    response = raid.update_raid_location(raid_id, from_id, location, client)
    
    if response.get('success'):
        leave_comment_and_update_messages(message_id, raid_id, from_username, 'Updated the raid location to {0}'.format(location_param), client)
        return msg.send_message(response.get('success'), chat_id, None)
    
    else:
        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def leave_comment_and_update_messages(message_id, raid_id, from_username, comment, client):
    
    if raid.insert_raid_comment(comment.strip()[:200].strip(), from_username, raid_id, client):
        update_tracked_messages(raid_id, client)

def update_tracked_messages(raid_id: int, client, allow_delete=False):
    
    message_tracking = raid.get_message_tracking_by_id(raid_id, client)
    
    if not message_tracking:
        return
    
    message = raid.format_raid_message(raid.get_raid_by_id(raid_id, client), client)

    for t in message_tracking:
        first_pair = next(iter((t.items())))
        msg.edit_message(first_pair[0], first_pair[1], message, 'MarkdownV2', True)
        
        if allow_delete:
            chat = msg.getChat(first_pair[0])
            if chat.get('result'):
                if chat['result']['type'] == 'channel':
                    msg.delete_message(first_pair[0], first_pair[1])
