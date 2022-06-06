import dynamo_functions as dynamo
import reply_to_message as reply

from datetime import datetime, timedelta

def garbage_collection():
    
    # First lets get a list of raids that have not been completed
    active_raids = dynamo.scan_attribute_not_exists('wokemon_raids', 'completed')
    
    if not active_raids:
        return

    for r in active_raids:
        # We will mark a raid as completed 10 minutes after the scheduled time
        raid_datetime = datetime.strptime(r.get('raid_detail').get('raid_datetime'), '%d/%m/%Y, %H:%M:%S')
        if (raid_datetime + timedelta(minutes = 10)) < datetime.now():
            dynamo.update_item('wokemon_raids', 'raid_id', r.get('raid_id'), 'completed', True)
            reply.update_tracked_messages(r.get('raid_id'), allow_delete=True)

    return True
