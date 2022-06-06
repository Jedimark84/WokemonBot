import os
import re

import message_functions as msg
import raid_function as raid

ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']

def callback_query_handler(callback_query: dict):
    
    try:
        
        # Check all mandatory fields exist in the callback_query message
        if not (all(x in callback_query for x in ['id', 'from', 'message', 'data'])):
            return
        
        callback_query_id      = callback_query['id']
        callback_query_from    = callback_query['from']
        callback_query_message = callback_query['message']
        callback_query_data    = callback_query['data']
        
        # Validate callback_query_data is a digit
        if not callback_query_data.isdigit():
            return msg.send_message('Received invalid callback_query_data: {0}'.format(callback_query_data), ADMIN_CHAT_ID)
        
        user_id = callback_query_from['id']
        chat_id = callback_query_message['chat']['id']
        msg_txt = callback_query_message["text"].split(';')[0]
        
        if re.match('^Raid\s(\d)+$', msg_txt):
            raid_id = msg_txt.split(' ')[1]
            
            if raid.join_raid(callback_query_from, int(raid_id), int(callback_query_data)):
                update_tracked_messages(raid_id)

        else:
            return msg.send_message('An unrecognised callback query was received: {0}'.format(callback_query), ADMIN_CHAT_ID)
    
    except Exception as e: raise
    
    finally:
        return msg.answer_callback_query(callback_query_id)

def update_tracked_messages(raid_id: int):
    
    print("In update_tracked_messages")
    
    raid_message = raid.format_raid_message(raid.get_raid_by_id(raid_id))

    for t in raid.get_message_tracking_by_id(raid_id):
        first_pair = next(iter((t.items())))
        msg.edit_message(first_pair[0], first_pair[1], raid_message, 'MarkdownV2', True)
