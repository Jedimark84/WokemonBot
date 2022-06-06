import boto3
import time

from decimal import Decimal

def scan_attribute_not_exists(table_name, attribute):

    start_time = time.time()

    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    response = table.scan(
        FilterExpression="attribute_not_exists(#field_name)",
        ExpressionAttributeNames = {
          '#field_name': attribute
        }
    )
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            FilterExpression="attribute_not_exists(#field_name)",
            ExpressionAttributeNames = {
              '#field_name': attribute
            }
        )
        data.extend(response['Items'])
    
    print("--- %s seconds for scan() ---" % round(time.time() - start_time, 2))
    
    return data

def get_item(table_name, partition_key_name, partition_key_value, optional_field_name=None):
    
    start_time = time.time()

    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    # If partition_key_value can be cast to a Decimal then do so
    if Decimal(partition_key_value):
        partition_key_value = Decimal(partition_key_value)

    response = table.get_item(
        Key = {
            partition_key_name: partition_key_value
        }
    )
    
    print(f"--- {round(time.time() - start_time, 2)} seconds for get_item({table_name}, {partition_key_name}, {partition_key_value}, {optional_field_name}) ---")

    if 'Item' not in response:
        return False

    if optional_field_name:
        if optional_field_name not in response['Item']:
            return False

        return response['Item'][optional_field_name]

    return response['Item']

def update_item(table_name, partition_key_name, partition_key_value, field_name, field_value):
    
    start_time = time.time()

    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    # If partition_key_value can be cast to a Decimal then do so
    if Decimal(partition_key_value):
        partition_key_value = Decimal(partition_key_value)

    response = table.update_item(
        Key = {
            partition_key_name: partition_key_value
        },
        UpdateExpression = f"set { field_name } = :x",
        ExpressionAttributeValues = {
            ':x': field_value
        },
        ReturnValues = 'ALL_NEW'
    )
    
    print(f"--- {round(time.time() - start_time, 2)} seconds for update_item({table_name}, {partition_key_name}, {partition_key_value}, {field_name}, {field_value}) ---")

    return True

def list_append(table_name, partition_key_name, partition_key_value, field_name, field_value):
    
    start_time = time.time()

    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    # If partition_key_value can be cast to a Decimal then do so
    if Decimal(partition_key_value):
        partition_key_value = Decimal(partition_key_value)

    response = table.update_item(
        Key = {
            partition_key_name: partition_key_value
        },
        UpdateExpression = "SET #field_name = list_append(if_not_exists(#field_name, :empty_list), :new_value)",
        ExpressionAttributeNames = {
          '#field_name': field_name
        },
        ExpressionAttributeValues = {
            ":empty_list": [],
            ":new_value": [ field_value ]
        },
        ReturnValues = 'ALL_NEW'
    )
    
    print(f"--- {round(time.time() - start_time, 2)} seconds for list_append({table_name}, {partition_key_name}, {partition_key_value}, {field_name}, {field_value}) ---")
    
    if response['ResponseMetadata']['HTTPStatusCode'] == 200 and 'Attributes' in response:
        return response
    
    return False

# TODO: Can we make these next 3 functions more generic...
def increment_list(table_name, partition_key_name, partition_key_value, list_index, telegram_id):
    
    start_time = time.time()
    
    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    # If partition_key_value can be cast to a Decimal then do so
    if Decimal(partition_key_value):
        partition_key_value = Decimal(partition_key_value)
    
    response = table.update_item(
        Key = {
            partition_key_name: partition_key_value
        },
        UpdateExpression = "SET #p_list[{0}].#id.additional = if_not_exists(#p_list[{0}].#id.additional, :initial) + :num".format(list_index),
        ExpressionAttributeNames = {
            '#p_list': 'raid_participants_list',
            '#id': 'telegram_id_{0}'.format(telegram_id)
        },
        ExpressionAttributeValues = {
            ":num": 1,
            ":initial": 0,
        },
        ReturnValues = 'ALL_NEW'
    )
    
    print(f"--- {round(time.time() - start_time, 2)} seconds for increment_list({table_name}, {partition_key_name}, {partition_key_value}, {list_index}, {telegram_id}) ---")
    
    if response['ResponseMetadata']['HTTPStatusCode'] == 200 and 'Attributes' in response:
        return response
    
    return False

def update_raid_participation(table_name, partition_key_name, partition_key_value, list_index, telegram_id, participation_type):
    
    start_time = time.time()

    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    # If partition_key_value can be cast to a Decimal then do so
    if Decimal(partition_key_value):
        partition_key_value = Decimal(partition_key_value)

    response = table.update_item(
        Key = {
            partition_key_name: partition_key_value
        },
        UpdateExpression = "SET #p_list[{0}].#id.participation_type = :participation_type".format(list_index),
        ExpressionAttributeNames = {
            '#p_list': 'raid_participants_list',
            '#id': 'telegram_id_{0}'.format(telegram_id)
        },
        ExpressionAttributeValues = {
            ":participation_type": participation_type
        },
        ReturnValues = 'ALL_NEW'
    )
    
    print(f"--- {round(time.time() - start_time, 2)} seconds for update_raid_participation({table_name}, {partition_key_name}, {partition_key_value}, {list_index}, {telegram_id}, {participation_type}) ---")
    
    if response['ResponseMetadata']['HTTPStatusCode'] == 200 and 'Attributes' in response:
        return response
    
    return False

def remove_additional(table_name, partition_key_name, partition_key_value, list_index, telegram_id):
    
    start_time = time.time()

    client = boto3.resource('dynamodb')
    table = client.Table(table_name)

    # If partition_key_value can be cast to a Decimal then do so
    if Decimal(partition_key_value):
        partition_key_value = Decimal(partition_key_value)

    response = table.update_item(
        Key = {
            partition_key_name: partition_key_value
        },
        UpdateExpression = "REMOVE #p_list[{0}].#id.additional".format(list_index),
        ExpressionAttributeNames = {
            '#p_list': 'raid_participants_list',
            '#id': 'telegram_id_{0}'.format(telegram_id)
        },
        ReturnValues = 'ALL_NEW'
    )
    
    print(f"--- {round(time.time() - start_time, 2)} seconds for remove_additional({table_name}, {partition_key_name}, {partition_key_value}, {list_index}, {telegram_id}) ---")
    
    if response['ResponseMetadata']['HTTPStatusCode'] == 200 and 'Attributes' in response:
        return response
    
    return False
