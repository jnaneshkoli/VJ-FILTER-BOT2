# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN
import asyncio
import logging

logger = logging.getLogger(__name__)

# First Database For File Saving 
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database For File Saving
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


async def save_file(media):
    """Save file in database"""

    file_id, file_ref = unpack_new_file_id((getattr(media, "file_id", "")))
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    caption = getattr(media, "caption", "")
    try:
        language = await detect_language(file_name)
    except:
        language = ['No match']

    file = Media(
        file_id=file_id,
        file_ref=file_ref,
        file_name=file_name,
        file_size=media.file_size,
        file_type=media.mime_type,
        caption=caption,
        language=language
    )

    try:
        await file.commit()
        # Check if this is a new file and trigger movie update post
        from info import AUTO_POST_MOVIES, MOVIE_UPDATE_CHANNEL
        if AUTO_POST_MOVIES and MOVIE_UPDATE_CHANNEL != 0:
            asyncio.create_task(post_to_movie_channel(file_name, file_id))
    except DuplicateKeyError:      
        logger.warning(
            '[File - %s] is already saved in database',
            file_name
        )
        return False, 2
    else:
        logger.info('[File - %s] is saved to database', file_name)
        return True, 0

async def post_to_movie_channel(file_name, file_id):
    """Post new movie file to update channel"""
    try:
        from bot import Client
        from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from info import MOVIE_UPDATE_CHANNEL, temp

        # Create a clean movie name for display
        movie_name = clean_movie_name(file_name)

        # Check if this movie already exists in channel and update/delete old post
        await check_and_update_existing_post(movie_name, file_id, file_name)

        # Create inline keyboard with download button
        buttons = [[
            InlineKeyboardButton('📥 Get File', url=f'https://telegram.me/{temp.U_NAME}?start=files_{file_id}')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)

        # Create message text
        message_text = f"🎬 **New Movie Added**\n\n"
        message_text += f"**📽️ Movie:** `{movie_name}`\n"
        message_text += f"**📁 File Name:** `{file_name}`\n"
        message_text += f"**🆔 File ID:** `{file_id}`\n\n"
        message_text += f"Click the button below to get the file!"

        # Send to movie update channel
        await Client.send_message(
            chat_id=MOVIE_UPDATE_CHANNEL,
            text=message_text,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error posting to movie channel: {e}")

def clean_movie_name(file_name):
    """Extract clean movie name from file name"""
    import re
    # Remove common file extensions and quality indicators
    clean_name = re.sub(r'\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v)$', '', file_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\b(720p|1080p|480p|360p|2160p|4k|hdrip|webrip|brrip|dvdrip|cam|ts|tc)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\b(hindi|english|tamil|telugu|malayalam|kannada|bengali)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\b(x264|x265|hevc|aac|ac3|dts)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    return clean_name

async def check_and_update_existing_post(movie_name, new_file_id, new_file_name):
    """Check if movie already posted and add new file to existing post"""
    try:
        from bot import Client
        from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from info import MOVIE_UPDATE_CHANNEL, temp
        import re

        # Search recent messages in the channel for the same movie
        async for message in Client.get_chat_history(MOVIE_UPDATE_CHANNEL, limit=100):
            if message.text and movie_name.lower() in message.text.lower():
                try:
                    # Extract existing file IDs from the message text
                    existing_files = []
                    file_id_pattern = r"🆔 File ID: `([^`]+)`"
                    existing_file_ids = re.findall(file_id_pattern, message.text)

                    # Extract existing file names
                    file_name_pattern = r"📁 File Name: `([^`]+)`"
                    existing_file_names = re.findall(file_name_pattern, message.text)

                    # Combine existing files
                    for i, file_id in enumerate(existing_file_ids):
                        if i < len(existing_file_names):
                            existing_files.append({
                                'id': file_id,
                                'name': existing_file_names[i]
                            })

                    # Add new file to the list
                    existing_files.append({
                        'id': new_file_id,
                        'name': new_file_name
                    })

                    # Create updated message text with all files
                    updated_text = f"🎬 **Movie Files Available**\n\n"
                    updated_text += f"**📽️ Movie:** `{movie_name}`\n\n"
                    updated_text += f"**📁 Available Files ({len(existing_files)}):**\n\n"

                    # Create buttons for each file
                    buttons = []
                    for idx, file_info in enumerate(existing_files, 1):
                        updated_text += f"**{idx}. File Name:** `{file_info['name']}`\n"
                        updated_text += f"**🆔 File ID:** `{file_info['id']}`\n\n"

                        # Create button for each file
                        file_size_info = get_file_size_info(file_info['name'])
                        button_text = f"📥 Get File {idx} ({file_size_info})"
                        buttons.append([InlineKeyboardButton(button_text, url=f"https://telegram.me/{temp.U_NAME}?start=files_{file_info['id']}")])

                    updated_text += f"**🔄 Last Updated:** Just now\n\n"
                    updated_text += f"Choose your preferred quality/size from the buttons below!"

                    reply_markup = InlineKeyboardMarkup(buttons)

                    # Edit the existing message with all files
                    await message.edit_text(
                        text=updated_text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Added new file to existing post for movie: {movie_name}")
                    return True  # Return True to indicate post was updated
                except Exception as e:
                    logger.error(f"Error updating existing post: {e}")

    except Exception as e:
        logger.error(f"Error checking existing posts: {e}")

    return False  # Return False to indicate no existing post was found/updated

def clean_file_name(file_name):
    """Clean and format the file name."""
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name)) 
    unwanted_chars = ['[', ']', '(', ')', '{', '}']

    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id, file_name):
    """Check if the file is already saved in either collection."""
    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            print(f"{file_name} is already saved.")
            return True

    return False

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""

    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]') 
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
    filter = {'file_name': regex}
    files = []
    if MULTIPLE_DATABASE:
        cursor1 = col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)
        cursor2 = sec_col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)

        for file in cursor1:
            files.append(file)
        for file in cursor2:
            files.append(file)
    else:
        cursor = col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)

        for file in cursor:
            files.append(file)

    total_results = col.count_documents(filter) if not MULTIPLE_DATABASE else (col.count_documents(filter) + sec_col.count_documents(filter))
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    return files, next_offset, total_results

async def get_bad_files(query, file_type=None, use_filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()

    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = rf'(\b|[.+-_]){query}(\b|[.+-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[s.+-_]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return [], 0

    filter_criteria = {'file_name': regex}
    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def count_documents(collection):
        return collection.count_documents(filter_criteria)

    total_results = (count_documents(col) + count_documents(sec_col) if MULTIPLE_DATABASE else count_documents(col))

    def find_documents(collection):
        return list(collection.find(filter_criteria))

    files = (find_documents(col) + find_documents(sec_col) if MULTIPLE_DATABASE else find_documents(col))

    return files, total_results

async def get_file_details(query):
    return col.find_one({'file_id': query}) or sec_col.find_one({'file_id': query})

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    """Return file_id"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id

# Placeholder for detect_language function if it's used elsewhere
async def detect_language(text):
    # Replace with actual language detection logic
    return ['English']

# Placeholder for Media class if it's used elsewhere
class Media:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def commit(self):
        # Replace with actual database commit logic
        pass

# Placeholder for Bot client if it's used elsewhere
class Client:
    async def send_message(self, **kwargs):
        pass

    async def get_chat_history(self, **kwargs):
        pass

# Placeholder for temp object if it's used elsewhere
class temp:
    U_NAME = "your_bot_username" # Replace with actual username

# Placeholder for logger if it's used elsewhere
class logger:
    @staticmethod
    def warning(msg, *args):
        print(f"WARNING: {msg % args}")

    @staticmethod
    def info(msg, *args):
        print(f"INFO: {msg % args}")

    @staticmethod
    def error(msg, *args):
        print(f"ERROR: {msg % args}")