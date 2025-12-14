import asyncio
import os
import sys
import json
import yaml
import pandas as pd
from datetime import datetime
from telethon import TelegramClient, events, types
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, DocumentAttributeFilename
from tqdm import tqdm

# Load Config
def load_config():
    with open('../config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()

# Proxy Setup
proxy = None
if config['proxy']['enable']:
    p_type = config['proxy']['type']
    import socks
    if p_type == 'socks5':
        proxy = (socks.SOCKS5, config['proxy']['address'].split(':')[0], int(config['proxy']['address'].split(':')[1]), True, config['proxy']['user'], config['proxy']['password'])
    elif p_type == 'http':
        proxy = (socks.HTTP, config['proxy']['address'].split(':')[0], int(config['proxy']['address'].split(':')[1]), True, config['proxy']['user'], config['proxy']['password'])

# Initialize Client
api_id = config['app_id']
api_hash = config['app_hash']
phone = config['phone_number']
session_file = '../output/anon'

client = TelegramClient(session_file, api_id, api_hash, proxy=proxy)

async def download_media_safe(client, message, output_dir, semaphore):
    async with semaphore:
        try:
            fname = "media"
            if message.file and message.file.name:
                fname = message.file.name
            elif message.file and message.file.ext:
                fname = f"{message.id}{message.file.ext}"
            
            file_size = message.file.size if message.file else 0
            
            # Use tqdm for real-time progress bar
            # position=0 to let tqdm handle multiple bars automatically (best effort)
            with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Msg {message.id} ({fname})", leave=False) as pbar:
                def progress_callback(current, total):
                    pbar.total = total
                    pbar.update(current - pbar.n)

                path = await client.download_media(
                    message, 
                    file=output_dir,
                    progress_callback=progress_callback
                )
            return path
        except Exception as e:
            print(f"\n[Error] Failed to download message {message.id}: {e}")
            return None

async def main():
    print("Connecting to Telegram via Python...")
    await client.start(phone=phone)
    print("Successfully logged in!")

    # 1. Select Dialog
    dialogs = []
    print("\nFetching dialogs...")
    async for d in client.iter_dialogs(limit=20):
        dialogs.append(d)
        print(f"[{len(dialogs)}] {d.name} (ID: {d.id})")

    choice = input("Select chat (number): ")
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(dialogs):
        print("Invalid selection.")
        return

    target = dialogs[int(choice)-1]
    print(f"Selected: {target.name}")

    # 2. Fetch Messages
    print("\nSelect Fetch Mode:")
    print("1. Earliest (Fetch all history from beginning)")
    print("2. From Date (Fetch messages after a specific date)")
    print("3. From Message ID (Fetch messages after a specific ID)")
    print("4. Latest (Fetch latest N messages)")
    
    mode_choice = input("Select mode (1-4): ")
    
    iter_args = {'entity': target}
    start_type = "unknown"

    if mode_choice == '1':
        start_type = 'earliest'
        iter_args['reverse'] = True
        print("Mode: Earliest (All history)")
        
    elif mode_choice == '2':
        start_type = 'date'
        iter_args['reverse'] = True
        date_str = input("Enter start date (YYYY-MM-DD): ")
        try:
            # Basic parsing
            if 'T' not in date_str and ' ' not in date_str:
                date_str += "T00:00:00"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            iter_args['offset_date'] = dt
            print(f"Starting from date: {dt}")
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return

    elif mode_choice == '3':
        start_type = 'message_id'
        iter_args['reverse'] = True
        msg_id = input("Enter start Message ID: ")
        if msg_id.isdigit():
            iter_args['min_id'] = int(msg_id)
            print(f"Starting from Message ID: {msg_id}")
        else:
            print("Invalid Message ID")
            return

    elif mode_choice == '4':
        start_type = 'latest'
        limit_str = input("Enter limit (default 100): ")
        limit = int(limit_str) if limit_str.isdigit() else 100
        iter_args['limit'] = limit
        print(f"Fetching latest {limit} messages")

    else:
        print("Invalid selection. Defaulting to latest 100.")
        iter_args['limit'] = 100

    messages_data = []
    media_messages = []
    
    count = 0
    async for msg in client.iter_messages(**iter_args):
        # Save Message Data
        msg_dict = {
            'id': msg.id,
            'date': msg.date,
            'message': msg.message,
            'sender_id': msg.sender_id,
            'reply_to': msg.reply_to_msg_id if msg.reply_to else None,
        }
        messages_data.append(msg_dict)

        # Check for Media
        if msg.media:
            media_messages.append(msg)
        
        count += 1
        if count % 100 == 0:
            print(f"Fetched {count} messages...", end='\r')
    
    print(f"\nTotal fetched: {count} messages.")

    # 3. Export HTML
    print(f"Exporting {len(messages_data)} messages to HTML...")
    if messages_data:
        df = pd.DataFrame(messages_data)
        
        # Convert date to string for better display
        if 'date' in df.columns:
            df['date'] = df['date'].astype(str)

        output_file = config['export_settings']['output_file']
        # Force .html extension if not present
        if not output_file.endswith('.html'):
            output_file = os.path.splitext(output_file)[0] + '.html'

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Simple HTML export with some styling
        html_content = df.to_html(escape=False, index=False)
        
        # Wrap in a basic HTML5 template
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Telegram Messages Export</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                img {{ max-width: 200px; }}
            </style>
        </head>
        <body>
            <h1>Exported Messages: {target.name}</h1>
            <p>Total Messages: {len(messages_data)}</p>
            {html_content}
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_html)
            
        print(f"Saved to {output_file}")
    else:
        print("No messages to export.")

    # 4. Download Media (Python Native)
    dl_cfg = config['download_settings']
    if media_messages and dl_cfg['max_concurrent_downloads'] > 0:
        print(f"\nStarting download of {len(media_messages)} media items...")
        
        dl_path = dl_cfg['download_path']
        os.makedirs(dl_path, exist_ok=True)
        
        sem = asyncio.Semaphore(dl_cfg['max_concurrent_downloads'])
        
        tasks = [download_media_safe(client, m, dl_path, sem) for m in media_messages]
        # Sort by size (Smallest first)
        # Messages without file info or size 0 will come first, which is fine
        print("Sorting files by size (Smallest first)...")
        media_messages.sort(key=lambda m: m.file.size if (m.file and hasattr(m.file, 'size')) else 0)

        dl_path = dl_cfg['download_path']
        os.makedirs(dl_path, exist_ok=True)
        
        sem = asyncio.Semaphore(dl_cfg['max_concurrent_downloads'])
        
        tasks = [download_media_safe(client, m, dl_path, sem) for m in media_messages]
        
        # Run tasks
        # We use gather here to let individual progress bars handle the display
        await asyncio.gather(*tasks)
            
    print("\nDone!")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())