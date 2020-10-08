# WokémonBot

## Summary:
A Pokémon Go Raid Bot for Telegram developed by the Woking, U.K. Pokémon Go community (Wokémon).

## Architecture:
The core functions of the bot are hosted within AWS. Messages sent directly to the Bot, or posted within groups the Bot is an admin of are sent as a HTTPS POST request to the AWS API Gateway Service where the JSON-serialized message is put onto a SQS queue. SQS is used in FIFO mode with content based dediplication enabled to prevent duplicate messages being processed. From SQS a Lambda function is triggered where the core functionality of the Bot exists. This repository hosts the source code for this Lambda function. The Lambda function has access to a MySQL RDS instance for data persistence. The Lambda function may respond via a HTTPS GET request to the Telegram API.

![Architecture](https://i.imgur.com/GtC1eUk.png)

## Instructions:

1. Creating a new raid

```/newraid [dd-Mmm-yy] hh:mm TITLE @ LOCATION```

Note: The date element is optional. If the raid is for today then just omit this parameter.

Examples:

```/newraid 16:45 Mega Charizard X @ Woking Park Sign```

```/newraid 25-Dec-20 12:00 Christmas Pikachu @ Ockenden```

2. Joining a raid
Use the buttons underneath the raid information message to participate, withdraw your participation or add a plus one to your participation.
Note: You will not be able to join the raid if the lobby is full (20 participants) or, if you are joining the remote lobby, the raid is full at 10 participants.

Button | Use
------------ | -------------
✅ | I am going to physically attend the raid.
📍 | I will join the raid remotely but I do not require an invite.
📩 | I would like to request an invite to join the remote lobby.
🚫 | I am dropping out of the raid.
➕ | I am bringing a plus one with me.

3. Commenting on a raid
If you quote the raid information message you can leave a comment (up to 100 characters) which will then be made visible in the original message for others to see.

4. Setting your nickname, level and team
PRO TIP: You can start a conversation directly with the bot to perform these commands. This will keep the group chat clear of clutter.
By default you will be known by your Telegram Username (if you have set one) or your Telegram First Name. We recommend you set your nickname to your in-game trainer name:

```/nickname Jedimark```

You can also set your trainer level (1 to 40) and team (valor, mystic or instinct):

```/level 40```

```/team valor```

5. Editing a raid
The raid creator has the ability to alter the time, title and location of a raid by quoting the raid information message and using the following commands:

```/time hh:mm```

```/title New Title```

```/location New Location```

Note: It is not possible to change the date of a raid.

6. Cancelling a raid
The raid creator has the ability to cancel a raid by quoting the raid information message and using the cancel command:

```/cancel```

7. Duplicate the raid message
You can duplicate the raid information message in any chat that the bot is a member of by using the following command:

```/raid id```

Note: The id is the first piece of information listed in the raid information message.
