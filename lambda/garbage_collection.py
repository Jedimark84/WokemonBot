import json
import os

import message_functions as msg
import database as db
import raid_function as raid

ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']

def garbage_collection():
    
    # First lets get a list of raids that need expiring
    raid_list = db.select('vw_raids_to_complete', { 'completed': 0 }, fetch_all=True)
    
    if not raid_list:
        return
    else:
        for r in raid_list:
            
            # First of all lets expire the raid by setting the completed flag
            db.update('raids', { 'completed': 1 }, { 'raid_id': r.get('raid_id') })
            
            # Now go through each message for the raid and do a final update
            message_list = db.select('message_tracking', { 'raid_id': r.get('raid_id') }, fetch_all=True)
            if message_list:
                
                formatted_message = raid.format_raid_message(raid.get_raid_by_id(r.get('raid_id')))
                
                for message in message_list:
                    db.update('message_tracking', { 'completed': 1 }, { 'message_id': message.get('message_id') })
                    
                    # If message is in a channel then delete the message, else edit the message
                    chat = msg.getChat(message.get('chat_id'))
                    if chat.get('result'):
                        if chat['result']['type'] == 'channel':
                            msg.delete_message(message.get('chat_id'), message.get('message_id'))
                        else:
                            msg.edit_message(message.get('chat_id'), message.get('message_id'), formatted_message, 'MarkdownV2')
    
    return True
