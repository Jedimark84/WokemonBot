import os
import re

import message_functions as msg
import raid_function as raid

from threading import Thread

ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']

def callback_query_handler(callback_query: dict, client):
    
    try:
        
        # Check all mandatory fields exist in the callback_query message
        if not (all(x in callback_query for x in ['id', 'from', 'message', 'data'])):
            return
        
        callback_query_id      = callback_query['id']
        callback_query_from    = callback_query['from']
        callback_query_message = callback_query['message']
        callback_query_data    = callback_query['data']
        
        # We provide no feedback to the user so answer the callback immediately
        Thread(target=msg.answer_callback_query, kwargs={'callback_query_id': callback_query_id}).start()
        #msg.answer_callback_query(callback_query_id)
        
        # Validate callback_query_data is a digit
        if not callback_query_data.isdigit():
            return msg.send_message('Received invalid callback_query_data: {0}'.format(callback_query_data), ADMIN_CHAT_ID)
        
        user_id = callback_query_from['id']
        chat_id = callback_query_message['chat']['id']
        msg_txt = callback_query_message["text"].split(';')[0]
        
        if re.match('^Raid\s(\d)+$', msg_txt):
            raid_id = msg_txt.split(' ')[1]
            
            if raid.join_raid(callback_query_from, int(raid_id), int(callback_query_data), client):
                return update_tracked_messages(raid_id, client)

        else:
            return msg.send_message('An unrecognised callback query was received: {0}'.format(callback_query), ADMIN_CHAT_ID)
    
    except Exception as e: raise

def update_tracked_messages(raid_id: int, client):
    
    print("In update_tracked_messages")
    
    raid_message = raid.format_raid_message(raid.get_raid_by_id(raid_id, client), client)
    
    threads = []

    for t in raid.get_message_tracking_by_id(raid_id, client):
        first_pair = next(iter((t.items())))
        threads.append(Thread(target=msg.edit_message, kwargs={
            'chat_id': first_pair[0], 'message_id': first_pair[1], 'text': raid_message, 'parse_mode': 'MarkdownV2', 'send_keyboard': True
        }))

    if threads:
        # Start all threads
        for x in threads:
            print("Starting a thread...")
            x.start()
        
        # Wait for all of them to finish
        for x in threads:
            x.join()
    
    print("All threads finished. Completed update_tracked_messages")
