import re
import string

from datetime import datetime
from datetime import date

import database as db

def get_raid_by_id(raid_id: int):
    return db.select('vw_raids', { 'raid_id': raid_id })

def get_raid_participants_by_id(raid_id: int):
    return db.select('vw_raiders', { 'raid_id': raid_id }, fetch_all=True)

def get_message_tracking_by_id(raid_id: int):
    return db.select('message_tracking', { 'raid_id': raid_id, 'completed': 0 }, fetch_all=True)

def get_raid_comments_by_id(raid_id: int):
    return db.select('raid_comments', { 'raid_id': raid_id }, fetch_all=True)

def get_raider_by_id(telegram_id: int):
    return db.select('raiders', { 'telegram_id': telegram_id })

def get_raid_participation_by_id(raid_id: int, raider_id: int):
    return db.select('raid_participants', { 'raid_id': raid_id, 'raider_id': raider_id })

def get_team_by_name(team: str):
    return db.select('teams', { 'team_name': team }, operator='LIKE')

def update_team(telegram_id, username, team):
    
    if not get_raider_by_id(telegram_id):
        insert_raider(telegram_id, username)
    
    team_dict = get_team_by_name(team)
    if team_dict:
        return db.update('raiders', { 'team_id': team_dict['team_id'] }, { 'telegram_id': telegram_id })
    
    return False

def update_level(telegram_id, username, level):
    
    if not get_raider_by_id(telegram_id):
        insert_raider(telegram_id, username)
    
    return db.update('raiders', { 'level': level }, { 'telegram_id': telegram_id })

def update_nickname(telegram_id, username, nickname):
    
    if not get_raider_by_id(telegram_id):
        insert_raider(telegram_id, username, nickname)
    else:
        return db.update('raiders', { 'nickname': escape(nickname, 32) }, { 'telegram_id': telegram_id })

def update_raid_participation(raid_id, raider_id, participation_type_id):
    return db.update('raid_participants', { 'participation_type_id': participation_type_id, 'party_count': 1 }, { 'raid_id': raid_id, 'raider_id': raider_id })

def update_raid_title(raid_id, from_id, title):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can perform this action." }
        else:
            result = db.update('raids', { 'raid_title': escape(title, 50) }, { 'raid_id': raid_id })
            if result:
                return { "success": "Raid title has been updated." }
            else:
                return { "error": "Raid title was not updated." }
    
    return { "error": "There was a problem updating the raid title. Please try again later." }

def update_raid_time(raid_id, from_id, time):
    
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
                result = db.update('raids', { 'raid_datetime': new_datetime.strftime("%Y/%m/%d, %H:%M:%S") }, { 'raid_id': raid_id })
                if result:
                    return { "success": "Raid time has been updated." }
                else:
                    return { "error": "Raid time was not updated." }
    
    return { "error": "There was a problem updating the raid time. Please try again later." }

def update_raid_location(raid_id, from_id, location):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can perform this action." }
        else:
            result = db.update('raids', { 'raid_location': escape(location, 50) }, { 'raid_id': raid_id })
            if result:
                return { "success": "Raid location has been updated." }
            else:
                return { "error": "Raid location was not updated." }
    
    return { "error": "There was a problem updating the raid location. Please try again later." }

def cancel_raid(raid_id, from_id):
    
    raid_dict = get_raid_by_id(raid_id)
    if not raid_dict:
        return { "error": "Could not find a raid with that id." }
    else:
        if not raid_dict.get('raid_creator_id') == int(from_id):
            return { "error": "Only the raid creator can perform this action." }
        else:
            result = db.update('raids', { 'cancelled': 1 }, { 'raid_id': raid_id })
            if result:
                return { "success": "Raid has been cancelled." }
            else:
                return { "error": "Raid was not cancelled." }
    
    return { "error": "There was a problem cancelling the raid. Please try again later." }

def increment_party_count(raid_id, raider_id):
    db.update_increment('raid_participants', 'party_count', { 'raid_id': raid_id, 'raider_id': raider_id })
    return True # TODO: return from calling function instead of having to return True

def insert_raid(raid_dict):
    
    # Step 1: Verify the user exists in the raiders table
    #         If they don't then create them!
    if not get_raider_by_id(raid_dict.get('raid_creator_id')):
        insert_raider(raid_dict.get('raid_creator_id'), raid_dict.get('raid_creator_username'))

    return db.insert('raids', { 'raid_creator_id': raid_dict.get('raid_creator_id'), \
                                'raid_datetime': raid_dict.get('raid_datetime').strftime("%Y/%m/%d, %H:%M:%S"), \
                                'raid_title': escape(raid_dict.get('raid_title'), 50), \
                                'raid_location': escape(raid_dict.get('raid_location'), 50) \
                                }, 'raid_id')

def insert_message_tracking(raid_id, chat_id, message_id):
    return db.insert('message_tracking', { 'raid_id': raid_id, 'chat_id': chat_id, 'message_id': message_id } )

def insert_raid_comment(comment, username, raid_id, comment_id):
    return db.insert('raid_comments', { 'comment_id': comment_id, 'raid_id': raid_id, 'username': escape(username, 32), 'comment': escape(comment, 200) } )

def insert_raid_participation(raid_id, raider_id, participation_type_id):
    return db.insert('raid_participants', { 'raid_id': raid_id, 'raider_id': raider_id, 'participation_type_id': participation_type_id, 'party_count': 1 } )

def insert_raider(telegram_id, username, nickname=None):
    if nickname:
        return db.insert('raiders', { 'telegram_id': telegram_id, 'username': escape(username, 32), 'nickname': escape(nickname, 32) } )
    else:
        return db.insert('raiders', { 'telegram_id': telegram_id, 'username': escape(username, 32) } )


def create_raid(raid_params, chat_id, raid_creator_id, raid_creator_username):
    
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
    
    if raid_dict.get('gym_name'):
        raid_location = '📍[{0}](https://www.google.com/maps/search/?api=1&query={1},{2})'.format(raid_dict.get('gym_name'), raid_dict.get('latitude'), raid_dict.get('longitude'))
    else:
        raid_location = raid_dict.get('raid_location')
    
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
            participation += ''.join('\n*⚠️The Remote Lobby is Full⚠️*\n' if (remote_count+invite_count) == 10 else '')
        
        raid_comments_dict = get_raid_comments_by_id(raid_dict.get('raid_id'))
        comments = ''
        if raid_comments_dict:
            for c in raid_comments_dict:
                comments += '{0}: _{1}_\n'.format(c['username'], c['comment'])
        
        completed = str()
        if raid_dict.get('completed') == 1:
            completed = 'RAID COMPLETED'
        
        final_string = '{0}\n{1}\n{2}'.format(participation, comments, completed)
    
    # IT IS VERY IMPORTANT THAT THE MESSAGE STARTS WITH 'Raid {raid_id};'
    # IT IS USED TO PARSE CALLBACK RESPONSES TO FIGURE OUT THE RAID ID
    return "*Raid* {0}; *Organiser:* {1}\n*Time & Title:* {2} \- {3}\n*Location:* {4}\n\n{5}".format(
                                            raid_dict.get('raid_id'), \
                                            '[{0}](tg://user?id={1})'.format(''.join([raid_dict.get('raid_creator_username') if not raid_dict.get('raid_creator_nickname') else raid_dict.get('raid_creator_nickname')]), raid_dict.get('raid_creator_id')),
                                            raid_datetime_string,
                                            raid_dict.get('raid_title'),
                                            raid_location,
                                            final_string
                                        )

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
        elif int(participation_type_id) == 0 and not p['participation_type_id'] == 4:
            # ... However, if they are in the remote lobby, then check there is space
            if p['participation_type_id'] == 2 or p['participation_type_id'] == 3:
                if remote_count >= 10:
                    return False
            
            return increment_party_count(raid_id, from_object['id'])
        
        # ... else they must be changing their participation type
        else:
            return update_raid_participation(raid_id, from_object['id'], participation_type_id)
    
    # I don't think it should be possible to get to this point
    return False

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
                                            "!": r"\\!",
                                            "'": r"\'"
                                        })).strip()

def get_username(input_json):
    # Some people haven't set a username, so use first_name instead
    if 'username' in input_json:
        from_username = input_json['username']
    else:
        from_username = input_json['first_name']

    return from_username
