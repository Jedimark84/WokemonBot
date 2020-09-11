import re
from datetime import datetime
from datetime import date
import database as db

def create_raid(raid_params, chat_id, raid_creator_id, raid_creator_username):
    
    # Stage 1: Validate Raid Params.
    
    # a) At a very basic level the raid params must be at least 10 chars.
    if len(raid_params) < 10:
        return { "error": "Correct format is as follows (note date is optional)\n/newraid dd-Mmm-yy hh:mm Raid Title @ Raid Location" }
    
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
    #    Also make a note of the raid_creator info - they will have admin rights for the raid
    raid_dict["raid_title"] = remaining.split('@')[0].strip()
    raid_dict["raid_location"] = remaining.split('@')[1].strip()
    raid_dict["raid_creator_id"] = raid_creator_id
    raid_dict["raid_creator_username"] = raid_creator_username
    
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

def update_team(telegram_id, username, team):
    
    # Step 1: Verify the user exists in the raiders table
    #.        If they don't then create them!
    if not get_raider_by_id(telegram_id):
        insert_raider(telegram_id, username)
    
    team_dict = get_team_by_name(team)
    if team_dict:
        
        # Connect to the database
        connection = db.connect()
        
        try:
            with connection.cursor() as cursor:
                # Update an existing record
                sql = "UPDATE `raiders` SET `team_id` = {0} WHERE (`telegram_id` = {1})".format(team_dict['team_id'], telegram_id)
                cursor.execute(sql)
            
            connection.commit()
            
            return True
        
        except Exception as e: raise
        
        finally:
            connection.close()
    
    return False

def update_level(telegram_id, username, level):
    
    # Step 1: Verify the user exists in the raiders table
    #.        If they don't then create them!
    if not get_raider_by_id(telegram_id):
        insert_raider(telegram_id, username)
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Update an existing record
            sql = "UPDATE `raiders` SET `level` = {0} WHERE (`telegram_id` = {1})".format(level, telegram_id)
            cursor.execute(sql)
        
        connection.commit()
        
        return True
    
    except Exception as e: raise
    
    finally:
        connection.close()
    
    return False

def update_nickname(telegram_id, username, nickname):
    
    # Step 1: Verify the user exists in the raiders table
    #         If they don't then create them!
    if not get_raider_by_id(telegram_id):
        insert_raider(telegram_id, username, nickname)
    else:
        
        # Connect to the database
        connection = db.connect()
        
        try:
            with connection.cursor() as cursor:
                # Update an existing record
                sql = "UPDATE `raiders` SET `nickname` = '{0}' WHERE (`telegram_id` = {1})".format(escape(nickname, 32), telegram_id)
                cursor.execute(sql)
            
            connection.commit()
            
            return True
        
        except Exception as e: raise
        
        finally:
            connection.close()
    
    return False

def insert_raid(raid_dict):
    
    # Step 1: Verify the user exists in the raiders table
    #         If they don't then create them!
    if not get_raider_by_id(raid_dict.get('raid_creator_id')):
        insert_raider(raid_dict.get('raid_creator_id'), raid_dict.get('raid_creator_username'))
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `raids` (`raid_creator_id`, `raid_datetime`, `raid_title`, `raid_location`) \
                    VALUES ({0}, '{1}', '{2}', '{3}')".format(
                        raid_dict.get('raid_creator_id'), \
                        raid_dict.get('raid_datetime').strftime("%Y/%m/%d, %H:%M:%S"), \
                        escape(raid_dict.get('raid_title'), 50), \
                        escape(raid_dict.get('raid_location'), 50)
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
            sql = "SELECT * FROM `vw_raids` WHERE `raid_id` = {0}".format(raid_id)
            cursor.execute(sql)
            result = cursor.fetchone()
    
    finally:
        connection.close()
    
    return result

def get_team_by_name(team):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `teams` WHERE `team_name` LIKE '{0}'".format(team)
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

def format_raider(raider_dict):
    
    player_str = '[{0}](tg://user?id={1})'.format(''.join([raider_dict.get('username') if not raider_dict.get('nickname') else raider_dict.get('nickname')]), raider_dict.get('raider_id'))
    player_str += ''.join(['' if not raider_dict.get('team_id') else ' {0}'.format(raider_dict.get('team_symbol'))])
    player_str += ''.join(['' if not raider_dict.get('level') else ' {0}'.format(str(raider_dict.get('level')))])
    player_str = ''.join(['{0} {1}'.format(player_str, 'with {0} other\(s\)'.format(raider_dict.get('party_count')-1)) if not raider_dict.get('party_count') == 1 else player_str])
    
    return player_str

def format_raid_message(raid_dict):
    
    if raid_dict.get('raid_datetime').date() == datetime.today().date():
        raid_datetime_string = raid_dict.get('raid_datetime').strftime("%H:%M")
    else:
        raid_datetime_string = raid_dict.get('raid_datetime').strftime("%d\-%b\-%y\, %H:%M")
    
    if raid_dict.get('cancelled') == 1:
        final_string = '❌ RAID CANCELLED ❌'
    else:
        raid_participant_dict = get_raid_participants_by_id(raid_dict.get('raid_id'))
        if not raid_participant_dict:
            participation = 'There are currently no participants for this raid\.'
        
        else:
            physical_count = 0
            remote_count   = 0
            invite_count   = 0
            dropout_count  = 0
            
            # Iterate through participants to get their status
            for p in raid_participant_dict:
                
                if p.get('participation_type_id') == 1:
                    physical_str = ''.join(['{0}\n{1}'.format(physical_str, format_raider(p)) if not physical_count == 0 else format_raider(p)])
                    physical_count += p.get('party_count')
                
                elif p.get('participation_type_id') == 2:
                    remote_str = ''.join(['{0}\n{1}'.format(remote_str, format_raider(p)) if not remote_count == 0 else format_raider(p)])
                    remote_count += p.get('party_count')
                
                elif p.get('participation_type_id') == 3:
                    invite_str = ''.join(['{0}\n{1}'.format(invite_str, format_raider(p)) if not invite_count == 0 else format_raider(p)])
                    invite_count += p.get('party_count')
                
                elif p.get('participation_type_id') == 4:
                    dropout_str = ''.join(['{0}\n{1}'.format(dropout_str, format_raider(p)) if not dropout_count == 0 else format_raider(p)])
                    dropout_count += p.get('party_count')
            
            participation = ''.join('*{0} Going In Person:*\n{1}\n'.format(physical_count, physical_str) if not physical_count == 0 else '')
            participation += ''.join('*{0} Joining Remotely:*\n{1}\n'.format(remote_count, remote_str) if not remote_count == 0 else '')
            participation += ''.join('*{0} Requesting an Invite:*\n{1}\n'.format(invite_count, invite_str) if not invite_count == 0 else '')
            participation += ''.join('*Dropped Out:*\n{0}\n'.format(dropout_str) if not dropout_count == 0 else '')
        
        raid_comments_dict = get_raid_comments_by_id(raid_dict.get('raid_id'))
        comments = ''
        if raid_comments_dict:
            for c in raid_comments_dict:
                comments += '{0}: _{1}_\n'.format(c['username'], c['comment'])
        final_string = '{0}\n{1}'.format(participation, comments)
    
    # IT IS VERY IMPORTANT THAT THE MESSAGE STARTS WITH 'Raid {raid_id};'
    # IT IS USED TO PARSE CALLBACK RESPONSES TO FIGURE OUT THE RAID ID
    return "*Raid* {0}; *Organiser:* {1}\n*Time and Title:* {2} \- {3}\n*Location:* {4}\n\n{5}".format(
                                            raid_dict.get('raid_id'), \
                                            '[{0}](tg://user?id={1})'.format(''.join([raid_dict.get('raid_creator_username') if not raid_dict.get('raid_creator_nickname') else raid_dict.get('raid_creator_nickname')]), raid_dict.get('raid_creator_id')),
                                            raid_datetime_string,
                                            raid_dict.get('raid_title'),
                                            raid_dict.get('raid_location'),
                                            final_string
                                        )

def cancel_raid(raid_id, from_id):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can cancel the raid." }
        else:
            # Connect to the database
            connection = db.connect()
            
            try:
                with connection.cursor() as cursor:
                    # Update an existing record
                    sql = "UPDATE `raids` SET `cancelled` = 1 WHERE `raid_id` = {0}".format(raid_id)
                    cursor.execute(sql)
                
                connection.commit()
                
                return { "success": "Raid Cancelled." }
            
            # If there is an error then raise it to the calling function.
            # It should get handled by the lambda_handler function.
            #except Exception as e: raise
            
            finally:
                connection.close()
    
    return { "error": "There was a problem cancelling the raid. Please try again later." }

def insert_message_tracking(raid_id, chat_id, message_id):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `message_tracking` (`raid_id`, `chat_id`, `message_id`) \
                    VALUES ({0}, {1}, {2})".format(raid_id, chat_id, message_id)
            cursor.execute(sql)
        
        connection.commit()
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
    
    finally:
        connection.close()

def get_message_tracking_by_id(raid_id):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `message_tracking` WHERE `raid_id` = {0}".format(raid_id)
            cursor.execute(sql)
            result = cursor.fetchall()
    
    finally:
        connection.close()
    
    return result

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
            # Update an existing record
            sql = "UPDATE `raid_participants` SET `participation_type_id` = {0}, `party_count` = 1 WHERE (`raid_id` = {1}) and (`raider_id` = {2})".format(participation_type_id, raid_id, raider_id)
            cursor.execute(sql)
        
        connection.commit()
        
        return True
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
    
    finally:
        connection.close()

def insert_raider(telegram_id, username, nickname=None):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            if nickname:
                sql = "INSERT INTO `raiders` (`telegram_id`, `username`, `nickname`) \
                            VALUES ({0}, '{1}', '{2}')".format(telegram_id, escape(username, 32), escape(nickname, 32))
            else:
                sql = "INSERT INTO `raiders` (`telegram_id`, `username`) \
                        VALUES ({0}, '{1}')".format(telegram_id, escape(username, 32))
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
    #         If they don't then create them!
    if not get_raider_by_id(from_object['id']):
        insert_raider(from_object['id'], get_username(from_object))
    
    # Step 2: If this is not a drop out request, is there space in the raid for another user?
    if int(participation_type_id) < 4:
        raid_dict = get_raid_participants_by_id(raid_id)
        if raid_dict:
            # Count physical raiders and remote raiders
            physical_count = 0
            remote_count = 0
            
            for r in raid_dict:
                if r['participation_type_id'] == 1:
                    physical_count += r['party_count']
                elif r['participation_type_id'] == 2 or r['participation_type_id'] == 3:
                    remote_count += r['party_count']
            
            # If there are already 20 people going, then the raid is full
            if (physical_count + remote_count) >= 20:
                # Raid lobby is full
                return False
            
            # If the user will be joining the remote lobby then check there are not 10 in it already
            if int(participation_type_id) == 2 or int(participation_type_id) == 3:
                if remote_count >= 10:
                    # Remote lobby is full
                    return False
    
    # There is space available in the raid!
    
    # Step 3: See if the user is already participating in this raid
    p = get_raid_participation_by_id(raid_id, from_object['id'])
    
    # If they are not participating already...
    if not p:
        # ... check the user is not trying to drop out of a raid they are not even ticked in for
        # ... or that they have pressed the +1 button
        if not (participation_type_id == '0' or participation_type_id == '4'):
            # Else we can add them to the raid
            return insert_raid_participation(raid_id, from_object['id'], participation_type_id)
    
    # If the user is already participating...
    else:
        # ... ignore duplicate requests
        if p.get('participation_type_id') == int(participation_type_id):
            return False
        
        # ... if they aren't a drop out, they can bring a plus 1?
        # ... However, if they are bringing a plus one into the remote lobby, then check there is space
        elif participation_type_id == '0' and not p['participation_type_id'] == 4:
            if participation_type_id == '2' or participation_type_id == '3':
                if remote_count >= 10:
                    return False
            else:
                return update_raid_with_a_plus_one(raid_id, from_object['id'], participation_type_id)
        
        # ... else they must be changing their participation type
        else:
            return update_raid_participation(raid_id, from_object['id'], participation_type_id)
    
    # I don't think it should be possible to get to this point
    return False

def update_raid_with_a_plus_one(raid_id, raider_id, participation_type_id):
    
    return (increment_party_count(raid_id, raider_id))

def increment_party_count(raid_id, raider_id):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Update an existing record
            sql = "UPDATE `raid_participants` SET `party_count` = `party_count` + 1 WHERE `raid_id` = {0} and `raider_id` = {1}".format(raid_id, raider_id)
            cursor.execute(sql)
        
        connection.commit()
        
        return True
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    #except Exception as e: raise
    
    finally:
        connection.close()

def insert_raid_comment(comment, username, raid_id, comment_id):
    
    # Connect to the database
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `raid_comments` (`comment_id`, `raid_id`, `username`, `comment`) \
                    VALUES ({0}, {1}, '{2}', '{3}')".format(comment_id, raid_id, escape(username, 32), escape(comment, 200))
            cursor.execute(sql)
        
        connection.commit()
        
        return True
    
    # If there is an error then raise it to the calling function.
    # It should get handled by the lambda_handler function.
    except Exception as e: raise
    
    finally:
        connection.close()

def escape(input, max_length):
    
    return input[:max_length].translate(str.maketrans({
                                            "_": r"\\_",
                                            "*": r"\\*",
                                            "[": r"\\[",
                                            "]": r"\\]",
                                            "(": r"\\(",
                                            ")": r"\\)",
                                            "~": r"\\~",
                                            "`": r"\\`",
                                            ">": r"\\>",
                                            "#": r"\\#",
                                            "+": r"\\+",
                                            "-": r"\\-",
                                            "=": r"\\=",
                                            "|": r"\\|",
                                            "{": r"\\{",
                                            "}": r"\\}",
                                            ".": r"\\.",
                                            "!": r"\\!"
                                        })).strip()

def get_raid_comments_by_id(raid_id):
    
    connection = db.connect()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `raid_comments` WHERE `raid_id` = {0}".format(raid_id)
            cursor.execute(sql)
            result = cursor.fetchall()
    
    finally:
        connection.close()
    
    return result

def change_raid_time(raid_id, from_id, time):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can perform this action." }
        else:
            # Verify the time is acceptable, not in the past
            current_datetime = raid_dict.get('raid_datetime')
            new_datetime = raid_dict.get('raid_datetime').replace(
                hour=int(time.split(':')[0]),
                minute=int(time.split(':')[1]),
                second=0,
                microsecond=0
            )
            if new_datetime < datetime.now():
                return { "error": "You cannot schedule a raid for the past." }
            else:
                
                # Connect to the database
                connection = db.connect()
                
                try:
                    
                    with connection.cursor() as cursor:
                        # Update an existing record
                        sql = "UPDATE `raids` SET `raid_datetime` = '{0}' WHERE `raid_id` = {1}".format(new_datetime.strftime("%Y/%m/%d, %H:%M:%S"), raid_id)
                        cursor.execute(sql)
                    
                    connection.commit()
                    
                    return { "success": "Raid time changed." }
                
                # If there is an error then raise it to the calling function.
                # It should get handled by the lambda_handler function.
                except Exception as e: raise
                
                finally:
                    connection.close()
    
    return { "error": "There was a problem changing the raid time. Please try again later." }

def change_raid_title(raid_id, from_id, title):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can perform this action." }
        else:
            
            # Connect to the database
            connection = db.connect()
            
            try:
                with connection.cursor() as cursor:
                    # Update an existing record
                    sql = "UPDATE `raids` SET `raid_title` = '{0}' WHERE `raid_id` = {1}".format(escape(title, 50), raid_id)
                    cursor.execute(sql)
                
                connection.commit()
                
                return { "success": "Raid title changed." }
            
            # If there is an error then raise it to the calling function.
            # It should get handled by the lambda_handler function.
            except Exception as e: raise
            
            finally:
                connection.close()
    
    return { "error": "There was a problem changing the raid title. Please try again later." }

def change_raid_location(raid_id, from_id, location):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can perform this action." }
        else:
            
            # Connect to the database
            connection = db.connect()
            
            try:
                with connection.cursor() as cursor:
                    # Update an existing record
                    sql = "UPDATE `raids` SET `raid_location` = '{0}' WHERE `raid_id` = {1}".format(escape(location, 50), raid_id)
                    cursor.execute(sql)
                
                connection.commit()
                
                return { "success": "Raid location changed." }
            
            # If there is an error then raise it to the calling function.
            # It should get handled by the lambda_handler function.
            except Exception as e: raise
            
            finally:
                connection.close()
    
    return { "error": "There was a problem changing the raid location. Please try again later." }


def get_username(input_json):
    # Some people haven't set a username, so use first_name instead
    if 'username' in input_json:
        from_username = input_json['username']
    else:
        from_username = input_json['first_name']

    return from_username

