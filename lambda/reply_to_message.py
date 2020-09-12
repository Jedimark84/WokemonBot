import os
import re
import message_functions as msg
import raid_function as raid

ADMIN_CHAT_ID    = os.environ['ADMIN_CHAT_ID']
RESPOND_TO_IDS   = [555076590, 1353986583]

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
        if not reply_to_message['from']['id'] in RESPOND_TO_IDS:
            return
        
        quoted_message_text = reply_to_message['text']
        text_split          = quoted_message_text.split(';')[0]
        
        if re.match('^Raid\s(\d)+$', text_split):
            
            raid_id       = text_split.split(' ')[1]
            chat_id       = chat['id']
            from_id       = from_obj['id']
            from_username = raid.get_username(from_obj)
            
            if reply_text == '/cancel':
                response = raid.cancel_raid(raid_id, from_id)
                
                if response.get('success'):
                    formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                    tracking = raid.get_message_tracking_by_id(raid_id)
                    for t in tracking:
                        msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                    return msg.send_message('Raid Cancelled.', chat_id, None)
                else:
                    return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)
            
            if reply_text.startswith('/time'):
                if not re.match('^/time\s([01]?[0-9]|2[0-3]):[0-5][0-9]$', reply_text):
                    return msg.send_message('ERROR: Please supply the time in the format: hh:mm', chat_id, None)
                else:
                    time = reply_text.replace('/time', '').strip()
                    response = raid.change_raid_time(raid_id, from_id, time)
                    if response.get('success'):
                        raid.insert_raid_comment('Changed the raid time to {0}'.format(time), from_username, raid_id, message_id)
                        formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                        tracking = raid.get_message_tracking_by_id(raid_id)
                        for t in tracking:
                            msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                        return msg.send_message('Raid time has been changed.', chat_id, None)
                    else:
                        return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)
            
            if reply_text.startswith('/title'):
                title = reply_text.replace('/title','').strip()[:50].strip()
                response = raid.change_raid_title(raid_id, from_id, title)
                if response.get('success'):
                    raid.insert_raid_comment('Changed the raid title to {0}'.format(title), from_username, raid_id, message_id)
                    formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                    tracking = raid.get_message_tracking_by_id(raid_id)
                    for t in tracking:
                        msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                    return msg.send_message('Raid title has been changed.', chat_id, None)
                else:
                    return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)
            
            if reply_text.startswith('/location'):
                location = reply_text.replace('/location','').strip()[:50].strip()
                response = raid.change_raid_location(raid_id, from_id, location)
                if response.get('success'):
                    raid.insert_raid_comment('Changed the raid location to {0}'.format(location), from_username, raid_id, message_id)
                    formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                    tracking = raid.get_message_tracking_by_id(raid_id)
                    for t in tracking:
                        msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
                    return msg.send_message('Raid location has been changed.', chat_id, None)
                else:
                    return msg.send_message('ERROR: {0}'.format(response.get('error')), chat_id, None)        
            
            if raid.insert_raid_comment(reply_text.strip()[:200].strip(), from_username, raid_id, message_id):
                formatted_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))
                tracking = raid.get_message_tracking_by_id(raid_id)
                for t in tracking:
                    msg.edit_message(t.get('chat_id'),t.get('message_id'),formatted_message,'MarkdownV2', True)
        else:
            msg.send_message('Unsupported reply_to_message message received: {0}'.format(message), ADMIN_CHAT_ID, None)
        
        return True
    
    except Exception as e: raise
