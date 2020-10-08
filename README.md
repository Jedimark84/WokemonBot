# WokémonBot

A Pokémon Go Raid Bot for Telegram developed by the Woking, U.K. Pokémon Go community (Wokémon).

The core functions of the bot are hosted within AWS. Messages sent directly to the Bot, or posted within groups the Bot is an admin of are sent as a HTTPS POST request to the AWS API Gateway Service where the JSON-serialized message is put onto a SQS queue. SQS is used in FIFO mode with content based dediplication enabled to prevent duplicate messages being received and processed by the Bot. From SQS a Lambda function is triggered where the core functionality of the Bot exists. This repository hosts the source code for this Lambda function. The Lambda function has access to a MySQL RDS instance for data persistence. The Lambda function may respond via a HTTPS GET request to the Telegram API.

![Architecture](https://i.imgur.com/GtC1eUk.png)
