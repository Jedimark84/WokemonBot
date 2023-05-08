import boto3
import re
import string
import uuid

from datetime import date, datetime

import dynamo_functions as dynamo

def update_raid_location(raid_id, from_id, location, client):
    
    raid_dict = get_raid_by_id(raid_id, client)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_detail').get('raid_creator_id') == from_id:
            return { "error": "Only the raid creator can perform this action." }
        else:
            result = dynamo.update_item('wokemon_raids', 'raid_id', raid_id, 'raid_detail.raid_location', escape(location, 50), client)
            if result:
                return { "success": "📍 Raid location has been updated." }
            else:
                return { "error": "Raid location was not updated." }
    
    return { "error": "There was a problem updating the raid location. Please try again later." }

def update_raid_time(raid_id, from_id, time, client):
    
    raid_dict = get_raid_by_id(raid_id, client)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_detail').get('raid_creator_id') == from_id:
            return { "error": "Only the raid creator can perform this action." }
        else:
            # Verify the time is acceptable, not in the past
            current_datetime = datetime.strptime(raid_dict.get('raid_detail').get('raid_datetime'), '%d/%m/%Y, %H:%M:%S')
            new_datetime = current_datetime.replace(
                hour=int(time.split(':')[0]),
                minute=int(time.split(':')[1]),
                second=0,
                microsecond=0
            )

            if new_datetime < datetime.now():
                return { "error": "You cannot schedule a raid for the past." }
            else:
                result = dynamo.update_item('wokemon_raids', 'raid_id', raid_id, 'raid_detail.raid_datetime', new_datetime.strftime("%d/%m/%Y, %H:%M:%S"), client)
                if result:
                    return { "success": "🕗 Raid time has been updated." }
                else:
                    return { "error": "Raid time was not updated." }
    
    return { "error": "There was a problem updating the raid time. Please try again later." }

def update_raid_title(raid_id, from_id, title, client):
    
    raid_dict = get_raid_by_id(raid_id, client)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_detail').get('raid_creator_id') == from_id:
            return { "error": "Only the raid creator can perform this action." }
        else:
            result = dynamo.update_item('wokemon_raids', 'raid_id', raid_id, 'raid_detail.raid_title', escape(title, 50), client)
            if result:
                return { "success": "📃 Raid title has been updated." }
            else:
                return { "error": "Raid title was not updated." }
    
    return { "error": "There was a problem updating the raid title. Please try again later." }

def cancel_raid(raid_id, from_id, client):
    
    raid_dict = get_raid_by_id(raid_id, client)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_detail').get('raid_creator_id') == from_id:
            return { "error": "Only the raid creator can perform this action." }
        else:
            result = dynamo.update_item('wokemon_raids', 'raid_id', raid_id, 'cancelled', True, client)
            if result:
                return { "success": "Raid has been cancelled." }
            else:
                return { "error": "Raid was not cancelled." }
    
    return { "error": "There was a problem cancelling the raid. Please try again later." }

def get_raid_by_id(raid_id: int, client):
    return dynamo.get_item('wokemon_raids', 'raid_id', raid_id, client=client)

def get_raid_comments_by_id(raid_id: int, client):
    return dynamo.get_item('wokemon_raids', 'raid_id', int(raid_id), 'raid_comments', client=client)

def insert_raid_comment(comment, username, raid_id, client):
    return dynamo.list_append('wokemon_raids', 'raid_id', raid_id, 'raid_comments', "{0}: {1}".format(escape(username, 32), escape(comment, 200)), client)

def get_message_tracking_by_id(raid_id: int, client):
    return dynamo.get_item('wokemon_raids', 'raid_id', int(raid_id), 'message_tracking', client=client)

def insert_message_tracking(raid_id, chat_id, message_id, client):
    return dynamo.list_append('wokemon_raids', 'raid_id', raid_id, 'message_tracking', {"{0}".format(chat_id) : message_id}, client)

def join_raid(from_object, raid_id, participation_type_id, client):
    
    print("In join_raid")
    
    # Step 1: Verify the user exists in the raiders table
    #         If they don't then create them!
    user = dynamo.get_item('wokemon_users', 'telegram_id', from_object['id'], client=client)
    if not user:
        user = dynamo.update_item('wokemon_users', 'telegram_id', from_object['id'], 'telegram_username', get_username(from_object), client).get('Attributes')
    
    # Get raid participation details
    raid_dict = get_raid_participants_by_id(raid_id, client)
    
    # Step 2: If this is not a drop out request, is there space in the raid for another user?
    if participation_type_id < 4 and raid_dict:

        # Count physical raiders and remote raiders
        physical_count = 0
        remote_count = 0
        
        for participant in raid_dict:
            for k, v in participant.items():
                if v['participation_type'] == 1:
                    physical_count += (1+v.get('additional', 0))
                elif v['participation_type'] == 2 or v['participation_type'] == 3:
                    remote_count += (1+v.get('additional', 0))

        # If there are already 20 people going, then the raid is full
        if (physical_count + remote_count) >= 20:
            # Raid lobby is full
            print("Player cannot join the raid because the lobby is full.")
            print("Completed join_raid")
            return False

        # If the user will be joining the remote lobby then check there are not 10 in it already
        if participation_type_id == 2 or participation_type_id == 3:
            if remote_count >= 10:
                # Remote lobby is full
                print("Player cannot join the raid because the remote lobby is full.")
                print("Completed join_raid")
                return False

    # There is space available in the raid!
    
    # Step 3: See if the user is already participating in this raid
    p = False
    list_index = 0
    if raid_dict:
        for participant in raid_dict:
            if participant.get('telegram_id_{0}'.format(str(from_object['id']))):
                p = participant.get('telegram_id_{0}'.format(str(from_object['id'])))
                p['list_index'] = list_index
            list_index+=1

    # If they are not participating already...
    if not p:
        # ... check the user is not trying to drop out of a raid they are not even ticked in for
        # ... or that they have pressed the +1 button
        if not (participation_type_id == 0 or participation_type_id == 4):
            # Else we can add them to the raid
            print("Adding new player to raid.")
            print("Completing join_raid by returning list_append")
            return dynamo.list_append('wokemon_raids', 'raid_id', raid_id, 'raid_participants_list', {"telegram_id_{0}".format(from_object['id']): {"participation_type": participation_type_id, "user_data": get_user_data(user)}}, client)
    
    # If the user is already participating...
    else:
        existing_participation_type = p.get('participation_type')
        # ... ignore duplicate requests
        if existing_participation_type == participation_type_id:
            print("Duplicate player request.")
            print("Completed join_raid")
            return False

        # ... if they aren't a drop out, they can bring a plus 1?
        elif participation_type_id == 0 and not existing_participation_type == 4:
            # ... However, if they are in the remote lobby, then check there is space
            if existing_participation_type == 2 or existing_participation_type == 3:
                if remote_count >= 10:
                    print("Player cannot bring a +1 because remote lobby is full.")
                    print("Completed join_raid")
                    return False

            print("Adding a players +1 to the raid.")
            print("Completing join_raid by returning increment_list")
            return dynamo.increment_list('wokemon_raids', 'raid_id', raid_id, p.get('list_index'), from_object['id'], client)
        
        # ... else they must be changing their participation type
        else:
            # if they were bringing additional people previously, remove these
            if 'additional' in p:
                print("Removing the players +1s from the raid.")
                dynamo.remove_additional('wokemon_raids', 'raid_id', raid_id, p.get('list_index'), from_object['id'], client)

            print("Chaning a players participation type.")
            print("Completing join_raid by returning update_raid_participation")
            return dynamo.update_raid_participation('wokemon_raids', 'raid_id', raid_id, p.get('list_index'), from_object['id'], participation_type_id, client)
    
    # I don't think it should be possible to get to this point
    return False
    
def get_raid_participants_by_id(raid_id: int, client):
    return dynamo.get_item('wokemon_raids', 'raid_id', int(raid_id), 'raid_participants_list', client=client)

def return_team_symbol(team_name: str):

    if team_name.casefold() == 'Valor'.casefold():
        return '🔴'
    elif team_name.casefold() == 'Mystic'.casefold():
        return '🔵'
    elif team_name.casefold() == 'Instinct'.casefold():
        return '🟡'
    
    return '?'

def get_user_data(user):
    data = user.get('telegram_username') if not user.get('trainer_name') else user.get('trainer_name')
    data += '' if not user.get('trainer_team') else f" {return_team_symbol(user.get('trainer_team'))}"
    data += '' if not user.get('trainer_level') else f" ({user.get('trainer_level')})"
    return data

def format_raider(telegram_id, participant_dict, client):

    telegram_id = telegram_id.replace('telegram_id_', '')
    user_dict = dynamo.get_item('wokemon_users', 'telegram_id', telegram_id, client=client)

    player_str = '[{0}](tg://user?id={1})'.format(''.join([user_dict.get('telegram_username') if not user_dict.get('trainer_name') else user_dict.get('trainer_name')]), user_dict.get('telegram_id'))
    player_str += ''.join(['' if not user_dict.get('trainer_team') else ' {0}'.format(return_team_symbol(user_dict.get('trainer_team')))])
    player_str += ''.join(['' if not user_dict.get('trainer_level') else ' {0}'.format(str(user_dict.get('trainer_level')))])
    player_str = ''.join(['{0} {1}'.format(player_str, 'with {0} other\(s\)'.format(participant_dict.get('additional'))) if 'additional' in participant_dict else player_str])

    return player_str

def format_raid_message(raid_dict, client):
    
    print("In format_raid_message")
    
    raid_detail = raid_dict.get('raid_detail')
    raid_participants_list = raid_dict.get('raid_participants_list')
    raid_comments = raid_dict.get('raid_comments')
    
    raid_datetime = datetime.strptime(raid_detail.get('raid_datetime'), '%d/%m/%Y, %H:%M:%S')
    if raid_datetime.date() == datetime.today().date():
        raid_datetime_string = raid_datetime.strftime("%H:%M")
    else:
        raid_datetime_string = raid_datetime.strftime("%d\-%b\-%y\, %H:%M")
    
    if raid_detail.get('gym_name'):
        raid_location = '📍[{0}](https://www.google.com/maps/search/?api=1&query={1},{2})'.format(raid_detail.get('gym_name'), raid_detail.get('latitude'), raid_detail.get('longitude'))
    else:
        raid_location = raid_detail.get('raid_location')
    
    if raid_dict.get('cancelled'):
        final_string = '❌ RAID CANCELLED ❌'
    else:
        
        if not raid_participants_list:
            participation = 'There are currently no participants for this raid\.'
        
        else:
            physical_count = 0
            remote_count   = 0
            invite_count   = 0
            dropout_count  = 0
            
            # Iterate through participants to get their status
            for p in raid_participants_list:
                for k, v in p.items():
                    if v['participation_type']==1:
                        physical_str = ''.join(['{0}\n{1}'.format(physical_str, format_raider(k, v, client)) if not physical_count == 0 else format_raider(k, v, client)])
                        physical_count += (1+v.get('additional')) if 'additional' in v else 1
                    
                    elif v['participation_type'] == 2:
                        remote_str = ''.join(['{0}\n{1}'.format(remote_str, format_raider(k, v, client)) if not remote_count == 0 else format_raider(k, v, client)])
                        remote_count += (1+v.get('additional')) if 'additional' in v else 1
                    
                    elif v['participation_type'] == 3:
                        invite_str = ''.join(['{0}\n{1}'.format(invite_str, format_raider(k, v, client)) if not invite_count == 0 else format_raider(k, v, client)])
                        invite_count += (1+v.get('additional')) if 'additional' in v else 1
                    
                    elif v['participation_type'] == 4:
                        dropout_str = ''.join(['{0}\n{1}'.format(dropout_str, format_raider(k, v, client)) if not dropout_count == 0 else format_raider(k, v, client)])
                        dropout_count += v.get('additional') if 'additional' in v else 1
            
            participation = ''.join('*{0} Going In Person:*\n{1}\n'.format(physical_count, physical_str) if not physical_count == 0 else '')
            participation += ''.join('*{0} Joining Remotely:*\n{1}\n'.format(remote_count, remote_str) if not remote_count == 0 else '')
            participation += ''.join('*{0} Requesting an Invite:*\n{1}\n'.format(invite_count, invite_str) if not invite_count == 0 else '')
            participation += ''.join('*Dropped Out:*\n{0}\n'.format(dropout_str) if not dropout_count == 0 else '')
            participation += ''.join('\n*⚠️The Remote Lobby is Full⚠️*\n' if (remote_count+invite_count) == 10 else '')
        
        comments = ''
        if raid_comments:
            for c in raid_comments:
                comments += '{0}: _{1}_\n'.format(c.split(":", 1)[0].strip(), c.split(":", 1)[-1].strip())
        
        completed = str()
        if raid_dict.get('completed'):
            completed = 'RAID COMPLETED'
        
        final_string = '{0}\n{1}\n{2}'.format(participation, comments, completed)
    print("Completed format_raid_message")
    ## IT IS VERY IMPORTANT THAT THE MESSAGE STARTS WITH 'Raid {raid_id};'
    ## IT IS USED TO PARSE CALLBACK RESPONSES TO FIGURE OUT THE RAID ID
    return "*Raid* {0}; *Organiser:* {1}\n*Time & Title:* {2} \- {3}\n*Location:* {4}\n\n{5}".format(
                                            raid_dict.get('raid_id'), \
                                            '[{0}](tg://user?id={1})'.format(raid_detail.get('raid_creator_username'), raid_detail.get('raid_creator_id')),
                                            raid_datetime_string,
                                            raid_detail.get('raid_title'),
                                            raid_location,
                                            final_string
                                        )

def create_raid(raid_params, chat_id, raid_creator_id, raid_creator_username, client):
    
    # Stage 1: Validate Raid Params.
    
    # a) At a very basic level the raid params must be at least 10 chars.
    if len(raid_params) < 10:
        return { "error": "Correct format is as follows (note: date is optional)\n/newraid dd-Mmm-yy hh:mm Raid Title @ Raid Location" }
    
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
    
    # Convert the datetime to a string for dynamodb
    raid_dict['raid_datetime'] = raid_dict.get('raid_datetime').strftime("%d/%m/%Y, %H:%M:%S")
    
    # f) Clear up some variables we no longer need
    raid_dict.pop('raid_date')
    raid_dict.pop('raid_time')
    raid_dict.pop('raid_date_provided')
    
    # g) There should be 2 params left, the title and the location.
    #    They should be separated by a single @ symbol.
    if not sum(map(lambda x : 1 if '@' in x else 0, remaining)) == 1:
        return { "error": "Please provide a raid title and raid location separated by a single @ symbol." }
    
    # h) If we are here we can parse the remaining params to get the raid title and raid location
    #    Also make a note of the raid_creator info - they will have admin rights for the raid
    raid_dict["raid_title"] = string.capwords(remaining.split('@')[0].strip())
    raid_dict["raid_location"] = string.capwords(remaining.split('@')[1].strip())
    raid_dict["raid_creator_id"] = raid_creator_id
    raid_dict["raid_creator_username"] = raid_creator_username
    
    # Stage 2: We have the information we need to create a raid.
    #          So lets do that and return the result back to the handler.
    return insert_raid(raid_dict, client)

def insert_raid(raid_dict, client):
    
    counter_value = dynamo.get_item('wokemon_counter', 'counter_id', 0, 'counter_value', client=client)
    raid_id = counter_value+1
    dynamo.update_item('wokemon_counter', 'counter_id', 0, 'counter_value', raid_id, client)
    
    response = dynamo.update_item('wokemon_raids', 'raid_id', raid_id, 'raid_detail', raid_dict, client)
    
    raid_dict["raid_id"] = raid_id
    
    return raid_dict

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

def escape(input, max_length):
    
    return input[:max_length].translate(str.maketrans({
                                            "_": r"\_",
                                            "*": r"\*",
                                            "[": r"\[",
                                            "]": r"\]",
                                            "(": r"\(",
                                            ")": r"\)",
                                            "~": r"\~",
                                            "`": r"\`",
                                            ">": r"\>",
                                            "#": r"\#",
                                            "+": r"\+",
                                            "-": r"\-",
                                            "=": r"\=",
                                            "|": r"\|",
                                            "{": r"\{",
                                            "}": r"\}",
                                            ".": r"\.",
                                            "!": r"\!",
                                            "'": r"\'"
                                        })).strip()

def get_username(input_json):
    # Some people haven't set a username, so use first_name instead
    if 'username' in input_json:
        from_username = input_json['username']
    else:
        from_username = input_json['first_name']

    return from_username
