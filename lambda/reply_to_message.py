import os
import re
import string

import message_functions as msg
import raid_function as raid

ADMIN_CHAT_ID       = os.environ['ADMIN_CHAT_ID']
RESPOND_ONLY_TO_IDS = [555076590, 1353986583] # IDs for @Wokemon_bot and @Wokedev_bot
SUPPORTED_COMMANDS  = ['cancel', 'time', 'title', 'location']

def reply_to_message_handler(message: dict):
    
    try:
        
        # Check all mandatory fields exist in the callback_query message
        if not (all(x in message for x in ['message_id', 'from', 'chat', 'reply_to_message', 'text'])):
            return
        
        message_id       = message['message_id']
        from_obj         = message['from']
        chat             = message['chat']
        reply_to_message = message['reply_to_message']
        reply_text       = message['text']
        
        # Check all mandatory fields exist in the reply_to_message
        if not (all(x in reply_to_message for x in ['message_id', 'from', 'chat', 'text'])):
            return
        
        # I only respond to a reply_to_message if the original message came from me
        if not reply_to_message['from']['id'] in RESPOND_ONLY_TO_IDS:
            return
        
        quoted_message_text = reply_to_message['text']
        text_split          = quoted_message_text.split(';')[0]
        
        # I only respond to raid information messages
        if re.match('^Raid\s(\d)+$', text_split):
            
            raid_id       = text_split.split(' ')[1]
            chat_id       = chat['id']
            from_id       = from_obj['id']
            from_username = raid.get_username(from_obj)
            
            # Is the reply a bot command?
            if reply_text.startswith('/'):
                
                # Get the bot command and check the command is supported
                bot_command = reply_text[1:].split(' ')[0].strip()
                bot_command_params = reply_text[1:].replace(bot_command, '').strip()
                
                if not any(x==bot_command for x in SUPPORTED_COMMANDS):
                    return
                
                if bot_command == 'cancel':
                    return bot_command_cancel(message_id, chat_id, raid_id, from_id)
                
                if bot_command == 'time':
                    return bot_command_time(message_id, chat_id, raid_id, from_id, from_username, bot_command_params)
                
                if bot_command == 'title':
                    return bot_command_title(message_id, chat_id, raid_id, from_id, from_username, bot_command_params)
                
                if bot_command == 'location':
                    return bot_command_location(message_id, chat_id, raid_id, from_id, from_username, bot_command_params)
            
            else:
                return leave_comment_and_update_messages(message_id, raid_id, from_username, reply_text)
        
        return
    
    except Exception as e: raise

def bot_command_cancel(message_id, chat_id, raid_id, from_id):
    
    response = raid.cancel_raid(raid_id, from_id)
    
    if response.get('success'):
        formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
        tracking = raid.get_message_tracking_by_id(raid_id)
        for t in tracking:
            msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
        
        return msg.send_message('Raid Cancelled.', chat_id, None)
    
    else:
        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def bot_command_time(message_id, chat_id, raid_id, from_id, from_username, time_param):
    
    if not re.match('^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_param):
        return msg.send_message('ERROR: Please supply the time in the format: hh:mm', chat_id, None)
    
    else:
        response = raid.change_raid_time(raid_id, from_id, time_param)
        
        if response.get('success'):
            leave_comment_and_update_messages(message_id, raid_id, from_username, 'Changed the raid time to {0}'.format(time_param))
            return msg.send_message('Raid time has been changed.', chat_id, None)
        
        else:
            return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def bot_command_title(message_id, chat_id, raid_id, from_id, from_username, title_param):
    
    title = string.capwords(title_param[:50].strip())
    response = raid.update_raid_title(raid_id, from_id, title)
    
    if response.get('success'):
        leave_comment_and_update_messages(message_id, raid_id, from_username, 'Updated the raid title to {0}'.format(title_param))
        return msg.send_message(response.get('success'), chat_id, None)
    
    else:
        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def bot_command_location(message_id, chat_id, raid_id, from_id, from_username, location_param):
    
    location = string.capwords(location_param[:50].strip())
    response = raid.change_raid_location(raid_id, from_id, location)
    
    if response.get('success'):
        leave_comment_and_update_messages(message_id, raid_id, from_username, 'Changed the raid location to {0}'.format(location_param))
        return msg.send_message('Raid location has been changed.', chat_id, None)
    
    else:
        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)

def leave_comment_and_update_messages(message_id, raid_id, from_username, comment):
    
    if raid.insert_raid_comment(comment.strip()[:200].strip(), from_username, raid_id, message_id):
        formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
        tracking = raid.get_message_tracking_by_id(raid_id)
        for t in tracking:
            msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
