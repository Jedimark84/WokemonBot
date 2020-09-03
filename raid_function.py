import re
from datetime import datetime
from datetime import date
import database_connection as db

def create_raid(raid_params, raid_creator_id):

    # Stage 1: Validate Raid Params.

    # a) At a very basic level the raid params must be at least 10 chars.
    if len(raid_params) < 10:
        return { "error": "Raid parameters provided too short to be valid." }

    # b) Validate the first param, it must either be a date or a time.
    raid_dict = determine_raid_date(raid_params.split(' ')[0])

    if raid_dict.get('error'):
        return { "error": raid_dict.get('error') }

    # c) Now remove the first param as it has been dealt with.
    remaining = raid_params.replace(raid_params.split(' ')[0], '').strip()

    # d) If we still need to parse the time param then do that.
    if not raid_dict.get('raid_time'):
        time = determine_raid_time(remaining.split(' ')[0])
        if time:
            raid_dict['raid_time'] = time
            remaining = remaining.replace(time, '').strip()
        else:
            return { "error": "You must provide a valid time." }

    # e) Create a date/time object and check it is sensible
    raid_dict['raid_datetime'] = raid_dict.get('raid_date').replace(
                                                hour=int(raid_dict.get('raid_time').split(':')[0]),
                                                minute=int(raid_dict.get('raid_time').split(':')[1]),
                                                second=0,
                                                microsecond=0
                                            )
    if raid_dict.get('raid_datetime') < datetime.now():
        return { "error": "You cannot schedule a raid for the past." }

    # f) Clear up some variables we no longer need
    raid_dict.pop('raid_date')
    raid_dict.pop('raid_time')
    raid_dict.pop('raid_date_provided')
    
    # g) There should be 2 params left, the title and the location.
    #    They should be separated by a single @ symbol.
    if not sum(map(lambda x : 1 if '@' in x else 0, remaining)) == 1:
        return { "error": "You must provide a raid title and raid location separated by a single @ symbol." }

    # h) If we are here we can parse the remaining params to get the raid title and raid location
    #    Also make a note of the raid_creator_id - they will have admin rights for the raid
    raid_dict["raid_title"] = remaining.split('@')[0].strip()
    raid_dict["raid_location"] = remaining.split('@')[1].strip()
    raid_dict["raid_creator_id"] = raid_creator_id

    # Stage 2: We have the information we need to create a raid.
    #          So lets do that and return the result back to the handler.
    return insert_raid(raid_dict)

def determine_raid_date(input):

    date_regex = r'^(([0-9])|([0-2][0-9])|([3][0-1]))\-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\-2[0-2]{1}$'
    find_date = re.match(date_regex, input.strip())
    
    if find_date:
        return {
            "raid_date_provided": True,
            "raid_date": datetime.strptime(find_date[0], '%d-%b-%y')
        }
    else:
        # Date was not provided first, is it a time?
        time = determine_raid_time(input)

        if time:
            return {
                "raid_date_provided": False,
                "raid_date": datetime.today(),
                "raid_time": time
            }
    
    # If we get to this point then the provided input is not valid
    return { "error": "Raid parameters must begin with a valid date and/or time." }

def determine_raid_time(input):
    time_regex = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    find_time = re.match(time_regex, input.strip())
    
    if find_time:
        return find_time[0]
    else:
        return False
        
def insert_raid(raid_dict):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `raids` (`raid_creator_id`, `raid_datetime`, `raid_title`, `raid_location`) \
                    VALUES ({0}, '{1}', '{2}', '{3}')".format(
                        raid_dict.get('raid_creator_id'), \
                        raid_dict.get('raid_datetime').strftime("%Y/%m/%d, %H:%M:%S"), \
                        raid_dict.get('raid_title'), \
                        raid_dict.get('raid_location')
                    )
            cursor.execute(sql)
        
        with connection.cursor() as cursor:
            # Grab the record we just created to pass back. We will want the raid_id from it.
            sql = "SELECT * FROM `raids` WHERE raid_id = @@Identity"
            cursor.execute(sql)
            result = cursor.fetchone()
    
        connection.commit()
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    except Exception as e: raise
        
    finally:
        connection.close()
    
    return result
    
def get_raid_by_id(raid_id):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `raids` WHERE `raid_id` = {0}".format(raid_id)
            cursor.execute(sql)
            result = cursor.fetchone()

    finally:
        connection.close()
        
    return result
    
def get_raid_participants_by_id(raid_id):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `vw_raiders` WHERE `raid_id` = {0}".format(raid_id)
            cursor.execute(sql)
            result = cursor.fetchall()

    finally:
        connection.close()
        
    return result

def list_raids():
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `raids` WHERE `raid_datetime` > now()"
            cursor.execute(sql)
            result = cursor.fetchall()

    finally:
        connection.close()
        
    return result

def format_raid_message(raid_dict):
    
    # TODO: This has become a mess - I need to refactor this!

    if raid_dict.get('raid_datetime').date() == datetime.today().date():
        raid_datetime_string = raid_dict.get('raid_datetime').strftime("%H:%M")
    else:
        raid_datetime_string = raid_dict.get('raid_datetime').strftime("%d\-%b\-%y\, %H:%M")
        
    raid_participant_dict = get_raid_participants_by_id(raid_dict.get('raid_id'))
    
    participation = 'There are currently no participants for this raid\.'
    if raid_participant_dict:
        participation = ''
        
        physical=False
        remote=False
        invite=False
        
        going_str = ""
        invite_str = ""
        remote_str = ""
        
        for p in raid_participant_dict:
            
            if p.get('participation_type_id') == 1:
                if not physical:
                    physical=True
                    going_str = "*Going In Person*"
                
                going_str += ('\n{0}'.format(p.get('username')))
                
            elif p.get('participation_type_id') == 2:
                if not remote:
                    remote=True
                    remote_str = "*Joining Remotely*"
                
                remote_str += ('\n{0}'.format(p.get('username')))
                
            elif p.get('participation_type_id') == 3:
                if not invite:
                    invite=True
                    invite_str = "*Requesting an Invite*"
                
                invite_str += ('\n{0}'.format(p.get('username')))

        participation += ('{0}\n{1}\n{2}'.format(going_str,remote_str,invite_str))
    
    # IT IS VERY IMPORTANT THAT THE MESSAGE STARTS WITH 'Raid {raid_id};'
    # IT IS USED TO PARSE CALLBACK RESPONSES TO FIGURE OUT THE RAID ID
    return "*Raid* {0}; *Organiser:* {1}\n*Title:* {2}\n*Time and Place:* {3} \@ {4}\n\n{5}".format(
                                            raid_dict.get('raid_id'), \
                                            raid_dict.get('raid_creator_id'),
                                            raid_dict.get('raid_title'),
                                            raid_datetime_string,
                                            raid_dict.get('raid_location'),
                                            participation
                                        )

def insert_message_tracking(raid_id, chat_id, message_id):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `message_tracking` (`raid_id`, `chat_id`, `message_id`) \
                    VALUES ({0}, '{1}', '{2}')".format(raid_id, chat_id, message_id)
            cursor.execute(sql)

        connection.commit()
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
        
    finally:
        connection.close()
        
def get_raid_participation_by_id(raid_id, raider_id):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `raid_participants` WHERE `raid_id` = {0} AND `raider_id` = {1}".format(raid_id, raider_id)
            cursor.execute(sql)
            result = cursor.fetchone()

    finally:
        connection.close()
        
    return result
        
def get_raider_by_id(id):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `raiders` WHERE `telegram_id` = {0}".format(id)
            cursor.execute(sql)
            result = cursor.fetchall()

    finally:
        connection.close()
        
    return result

def update_raid_participation(raid_id, raider_id, participation_type_id):

    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "UPDATE `raid_participants` SET `participation_type_id` = {0} WHERE (`raid_id` = {1}) and (`raider_id` = {2})".format(participation_type_id, raid_id, raider_id)
            cursor.execute(sql)

        connection.commit()
        
        return True
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
        
    finally:
        connection.close()
    
def insert_raider(user_info):
    
    telegram_id = user_info['id']
    username = user_info['username']
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `raiders` (`telegram_id`, `username`) \
                    VALUES ({0}, '{1}')".format(telegram_id, username)
            cursor.execute(sql)

        connection.commit()
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
        
    finally:
        connection.close()

def insert_raid_participation(raid_id, raider_id, participation_type_id):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `raid_participants` (`raid_id`, `raider_id`, `participation_type_id`, `party_count`) \
                    VALUES ({0}, {1}, {2}, {3})".format(raid_id, raider_id, participation_type_id, 1)
            cursor.execute(sql)

        connection.commit()
        
        return True
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
        
    finally:
        connection.close()

def join_raid(from_object, raid_id, participation_type_id):
    
    # Step 1: Verify the user exists in the raiders table
    #.        If they don't then create them!
    if not get_raider_by_id(from_object['id']):
        insert_raider(from_object)
        
    # Step 2: See if the user is already participating in the raid
    #         They may have changed their participation type
    #         Or just sending a duplicate request which we should ignore
    #         If they are not already participating - then add them
    p = get_raid_participation_by_id(raid_id, from_object['id'])
    if not p:
        return insert_raid_participation(raid_id, from_object['id'], participation_type_id)
    else:
        if p.get('participation_type_id') == int(participation_type_id):
            return False
        else:
            return update_raid_participation(raid_id, from_object['id'], participation_type_id)
    
    # We should never get here!
    return False