import datetime
import sys
import time
import slack_sdk
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

# *1 If not installed on your environment, bot needs those clients:
# slack_sdk
# datetime
# note that the clients might change or be updated

# Path of your project
sys.path.append(r'C:\Users\xxxxxxxxxxxxxxxxxxxxxxx')

# *2 API Token of your automator. Proper one should start at xoxb
SLACK_API_TOKEN = 'xoxb-xxxxxxxxxxxxxxxxxxxxxxxxxxx'

# Period, in days after which channels will be archived
ARCHIVE_LAST_MESSAGE_AGE_DAYS = 360

oldest_message_time_to_prevent_archive = (
    datetime.datetime.now() - datetime.timedelta(days=ARCHIVE_LAST_MESSAGE_AGE_DAYS)
).timestamp()

client = WebClient(SLACK_API_TOKEN)

my_user_id = client.auth_test()['user_id']


def post_archive_message(channel_name):
    message = (
        f"The Slack channel '{channel_name}' has been archived due to long inactivity.\n\n"
        "If you have any questions, doubts, or if you wish to unarchive the channel, "
        "please feel free to raise an IT ticket at [IT Ticket System](xxxxxxxxxxxx)."
    )
    response = client.chat_postMessage(channel=f"#{channel_name}", text=message)
    print(response)


def channel_has_recent_messages(channel_id):
    # Getting up to 2 messages younger than ARCHIVE_LAST_MESSAGE_AGE_DAYS
    global response

    real_messages = []
    try:
        response = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest_message_time_to_prevent_archive),
            limit=5
        )
        # Filter out message about our bot joining this channel
        if response["messages"] is not None:
            for m in response["messages"]:
                if 'user' not in m or m['user'] != my_user_id:
                    real_messages.append(m)
            if real_messages:
                print('#' + channel['name'] + ': Has recent messages')
            time.sleep(2)
        else:
            print("No conversation history")
    except slack_sdk.errors.SlackApiError as e:
        print(e)

    # If we found at least one - return True, if not - False
    return any(message for message in real_messages)

# *3 logic on ratelimiting overwrite
max_retries = 1
retry_delay = 61
next_cursor = None

response = client.conversations_list(
    exclude_archived=True,
    limit=999,
    types=["public_channel", "private_channel"]
)

for page in response:
    print('Going to next page....')
    for channel in page['channels']:
        if not channel['is_member']:
            for retry_count in range(max_retries):
                try:
                    client.conversations_join(channel=channel['id'])
                except slack_sdk.errors.SlackApiError as e:
                    print(f"Slack API error while joining channel {channel['name']}: {e.response['error']}")
                    if retry_count < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print("Max retries reached. Skipping this channel.")
                        continue
        if channel_has_recent_messages(channel['id']):
            print('#' + channel['name'] + ': looks active')
        else:
            print('There is no messages or threads found in #' + channel['name'])
            print('#' + channel['name'] + ': archiving')

            try:
                for retry_count in range(max_retries):
                    try:
                        client.conversations_archive(channel=channel['id'])
                        post_archive_message(channel['name'])  # Post the archive message
                        break
                    except slack_sdk.errors.SlackApiError as e:
                        print(f"Slack API error while archiving channel {channel['name']}: {e.response['error']}")
                        if retry_count < max_retries - 1:
                            print(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            print("Max retries reached. Skipping this channel.")
                            break  # Skip to the next channel
            except Exception:
                print("There is no slack message")
