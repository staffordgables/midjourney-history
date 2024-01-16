import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
from PIL import Image
import os
import time
import asyncio
from datetime import datetime
import logging
import pytz
import nacl

logging.basicConfig(level=logging.INFO)

discord_token = "YOURDISCORDBOTTOKEN"

load_dotenv()
client = commands.Bot(command_prefix="*", intents=discord.Intents.all())
directory = os.getcwd()
print(directory)

# Process images based on date range
async def process_images_by_date(start_date, end_date):
    for guild in client.guilds:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                await process_channel(channel, start_date, end_date, output_folder)

async def process_channel(channel, start_date, end_date):
    async for msg in channel.history(limit=None):
        for attachment in msg.attachments:
            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                created_at = attachment.created_at

                if start_date <= created_at <= end_date:
                    await download_image(attachment.url, attachment.filename)

# Process channel messages based on date range
async def process_channel_by_date(channel, start_date, end_date, output_folder):
    async for msg in channel.history(limit=None):
        for attachment in msg.attachments:
            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                created_at = msg.created_at  # Use the created_at of the message

                if start_date <= created_at <= end_date:
                    # Check if the message contains "Upscaled by" or "Image #"
                    if "Upscaled by" in msg.content or "Image #" in msg.content:
                        await download_image(attachment.url, attachment.filename, output_folder, msg)  # Pass 'msg' as an argument
                        print(f"Downloaded and processed: {attachment.filename}")
                    else:
                        await download_image(attachment.url, attachment.filename, output_folder, msg)  # Pass 'msg' as an argument
                        print(f"Downloaded and processed: {attachment.filename}")
                    
    # Add a message when all images have been processed
    print("##################")
    print("###           ###")
    print("###  D O N E  ###")
    print("###           ###")
    print("#################")

async def download_image(url, filename, output_folder, message):
    response = requests.get(url)
    if response.status_code == 200:
        # Define the input folder paths
        input_folder = f"input_{message.channel.name}_{message.channel.id}"
        output_folder = f"output_{message.channel.name}_{message.channel.id}"

        # Check if the output folder exists, and create it if necessary
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Check if the input folder exists, and create it if necessary
        if not os.path.exists(input_folder):
            os.makedirs(input_folder)
       
        output_path = os.path.join(output_folder, filename)
        
        if not os.path.exists(output_path):
            with open(f"{directory}/{input_folder}/{filename}", "wb") as f:
                f.write(response.content)
            print(f"Image downloaded: {filename}")
            input_file = os.path.join(input_folder, filename)

            if "Image #" not in message.content:
                file_prefix = os.path.splitext(filename)[0]
                # Split the image
                top_left, top_right, bottom_left, bottom_right = split_image(input_file)
                # Save the output images with dynamic names in the output folder
                top_left.save(os.path.join(output_folder, file_prefix + "_0.png"))
                top_right.save(os.path.join(output_folder, file_prefix + "_1.png"))
                bottom_left.save(os.path.join(output_folder, file_prefix + "_2.png"))
                bottom_right.save(os.path.join(output_folder, file_prefix + "_3.png"))
            else:
                try:
                    os.rename(f"{directory}/{input_folder}/{filename}", f"{directory}/{output_folder}/{filename}")
                except FileNotFoundError as e:
                    print(f"Error renaming the file: {e}")
         
             # Delete the input file if it exists
            if os.path.exists(f"{directory}/{input_folder}/{filename}"):
                os.remove(f"{directory}/{input_folder}/{filename}")

        else:
            # Print a message indicating the file was skipped
            print(f"Skipped {filename} - already present in the output folder.")

def split_image(image_file):
    with Image.open(image_file) as im:
        # Get the width and height of the original image
        width, height = im.size
        # Calculate the middle points along the horizontal and vertical axes
        mid_x = width // 2
        mid_y = height // 2
        # Split the image into four equal parts
        top_left = im.crop((0, 0, mid_x, mid_y))
        top_right = im.crop((mid_x, 0, width, mid_y))
        bottom_left = im.crop((0, mid_y, mid_x, height))
        bottom_right = im.crop((mid_x, mid_y, width, height))
        return top_left, top_right, bottom_left, bottom_right

async def handle_special_image(input_file, output_folder, filename):     
    os.rename(input_file, os.path.join(output_folder, filename))

@client.event
async def on_ready():
    print("Bot connected")
    
@client.event
async def on_message(message):
    logging.info(message.content)
    
    # Determine the output folder based on the channel's ID
    # The folder has format channelname_uniqueid this is due to perhaps channel naming across servers
    output_folder = f"output_{message.channel.name}_{message.channel.id}"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Process images based on dynamic date range if message contains "datehistory"
    if "datehistory:" in message.content:
        date_range = message.content.split(":")[1].strip()  # Extract the date range

        try:
            start_date_str, end_date_str = date_range.split(" to ")
            tz = pytz.timezone('US/Eastern')  # Replace 'YOUR_TIMEZONE' with your desired timezone, e.g., 'US/Eastern'
            start_date = tz.localize(datetime.strptime(start_date_str, "%Y-%m-%d"))
            end_date = tz.localize(datetime.strptime(end_date_str, "%Y-%m-%d"))
            print(f"Start Date: {start_date}, End Date: {end_date}")

            await process_channel_by_date(message.channel, start_date, end_date, output_folder)
            
            # Send a completion message to the channel
            await message.channel.send("Processing complete!")
            
        except ValueError as e:
            print(f"Error: {e}")
            return
   
    for attachment in message.attachments:
        if "Upscaled by" in message.content:
            file_prefix = 'UPSCALED_'
        else:
            file_prefix = ''
        
        if "Image #" in message.content and attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            try:
                response = requests.get(attachment.url)
                if response.status_code == 200:
                    output_folder = f"output_{message.channel.name}_{message.channel.id}"
                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)
                    with open(os.path.join(output_folder, attachment.filename), "wb") as f:
                        f.write(response.content)
            except:
                await asyncio.sleep(10)
                continue
        elif attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            try:
                response = requests.get(attachment.url)
                if response.status_code == 200:
                    input_folder = f"input_{message.channel.name}_{message.channel.id}"
                    output_folder = f"output_{message.channel.name}_{message.channel.id}"
                    if not os.path.exists(input_folder):
                        os.makedirs(input_folder)
                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)
                    with open(f"{directory}/{input_folder}/{attachment.filename}", "wb") as f:
                        f.write(response.content)
                    print(f"Image downloaded: {attachment.filename}")
                    input_file = os.path.join(input_folder, attachment.filename)
                    file_prefix = os.path.splitext(attachment.filename)[0]
                    top_left, top_right, bottom_left, bottom_right = split_image(input_file)
                    top_left.save(os.path.join(output_folder, file_prefix + "_0.png"))
                    top_right.save(os.path.join(output_folder, file_prefix + "_1.png"))
                    bottom_left.save(os.path.join(output_folder, file_prefix + "_2.png"))
                    bottom_right.save(os.path.join(output_folder, file_prefix + "_3.png"))
                    os.remove(f"{directory}/{input_folder}/{attachment.filename}")
            except:
                await asyncio.sleep(10)
                continue
                
            # Save the message content as a text file
            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                try:
                    # Create a folder to store text files if it doesn't exist
                    text_folder = "message_text"
                    if not os.path.exists(text_folder):
                        os.makedirs(text_folder)

                    # Save the message content to a text file
                    message_text = message.content
                    text_filename = f"{attachment.filename}.txt"
                    with open(os.path.join(text_folder, text_filename), "w", encoding="utf-8") as text_file:
                        text_file.write(message_text)
                except Exception as e:
                    print(f"Error saving message text: {e}")

@client.command()
async def explain_datehistory(ctx):
    explanation = "The `datehistory` format is used to specify a date range for processing images. " \
                   "It should be in the format: `datehistory: YYYY-MM-DD to YYYY-MM-DD`.\n" \
                   "For example: `datehistory: 2023-07-10 to 2023-07-11` will process images " \
                   "created between July 10, 2023, and July 11, 2023."
    await ctx.send(explanation)


client.run(discord_token)
