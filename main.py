from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import discord
import time
from collections import deque
import pyperclip
import os
from flask import Flask
from threading import Thread

# Flask app to keep bot alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Discord setup
DISCORD_TOKEN = os.environ['DISCORD_TOKEN']  # Get token from environment variables
CHANNEL_ID = 1339913139096916010

# Setup all required intents
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# Queue for storing emails
email_queue = deque()
is_processing = False

def enter_verification_code(driver, code):
    try:
        # Find all verification input boxes
        inputs = driver.find_elements(By.CSS_SELECTOR, "input.verify-input")
        
        # Enter each digit of the code
        for i, digit in enumerate(code):
            inputs[i].send_keys(digit)
            time.sleep(0.5)
            
        # Click Continue button after entering code
        continue_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.verify-email-button.default-btn"))
        )
        continue_button.click()
            
        print(f"✅ Verification code entered and continued")
        return True
    except Exception as e:
        print(f"❌ Error entering verification code: {str(e)}")
        return False

async def create_account(email, channel):
    global is_processing
    is_processing = True
    
    # Setup Chrome with Railway-specific options
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    
    # Start browser
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Go to website
        driver.get("https://www.topmediai.com/")
        wait = WebDriverWait(driver, 5)
        
        # Click login
        js_link = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='javascript:;']"))
        )
        js_link.click()
        
        # Click create account
        create_account = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.href-text"))
        )
        create_account.click()
        
        # Enter email
        email_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.sign-email"))
        )
        email_input.clear()
        email_input.send_keys(email)
        
        # Enter password
        password_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.sign-password"))
        )
        password_input.clear()
        password_input.send_keys("xBymkE9u3wtSzfi")
        
        # Click create button
        create_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.creat-button.default-btn"))
        )
        create_button.click()
        
        await channel.send("👀 Click create account button and waiting for verification code...")
        
        # Wait for verification code from Discord
        verification_code = None
        while verification_code is None:
            time.sleep(1)
            
            async for message in channel.history(limit=1):
                if message.content.isdigit() and len(message.content) == 6:
                    verification_code = message.content
                    break
        
        # Enter verification code
        if verification_code:
            time.sleep(2)
            enter_verification_code(driver, verification_code)
        
        # Click on API menu
        api_menu = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li.menu-list.tts-api"))
        )
        api_menu.click()
        
        # Wait for new tab to open
        time.sleep(1)
        
        # Switch to new tab
        new_tab = driver.window_handles[-1]
        driver.switch_to.window(new_tab)
        
        # Wait longer for page to load completely
        time.sleep(4)
        
        # Wait and click on Get API Key button
        get_api_key = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.base-bt.get-api-key"))
        )
        time.sleep(1)
        get_api_key.click()
        
        # Wait for Copy API Key button
        time.sleep(3)
        copy_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Copy the API Key']"))
        )
        copy_button.click()
        
        # Wait for clipboard content
        time.sleep(1)
        api_key = pyperclip.paste()
        
        if api_key:
            clean_api_key = api_key.strip()
            await channel.send(clean_api_key)
        else:
            await channel.send("Could not get API key")
        
        is_processing = False
        
        # Process next email if any in queue
        if email_queue:
            next_email = email_queue.popleft()
            await create_account(next_email, channel)
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        await channel.send(f"❌ Error in process: {str(e)}")
        is_processing = False
        return False
    finally:
        time.sleep(2)
        driver.quit()

@client.event
async def on_ready():
    print(f'🤖 Bot is ready: {client.user}')
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🟢 Bot is online and waiting for emails...")

@client.event
async def on_message(message):
    global is_processing
    
    if message.author == client.user:
        return
        
    if message.channel.id != CHANNEL_ID:
        return
    
    content = message.content.strip()
    
    if '@' in content:
        if not is_processing:
            try:
                success = await create_account(content, message.channel)
            except Exception as e:
                await message.channel.send(f"❌ Error creating account: {str(e)}")
        else:
            email_queue.append(content)

if __name__ == "__main__":
    keep_alive()  # Start the Flask server
    client.run(DISCORD_TOKEN)