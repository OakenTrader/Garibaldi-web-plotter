import requests
import time
import random
import os

# --- Configuration ---
# The URL of the website you want to "ping" or access.
# Make sure to include the full protocol (e.g., 'http://' or 'https://').
TARGET_URL = os.getenv("TARGET_URL", "https://example.com")

# The maximum delay between pings in minutes.
# The script will choose a random delay between 1 second and this maximum.
MAX_DELAY_MINUTES = 14

def ping_website(url):
    """
    Sends an HTTP GET request to the specified URL to check its status.
    """
    try:
        # We use a timeout to prevent the script from hanging indefinitely
        # if the website is slow to respond.
        response = requests.get(url, timeout=10)
        
        # Check the HTTP status code
        if response.status_code == 200:
            print(f"Successfully accessed {url}. Status Code: {response.status_code}")
        else:
            print(f"Failed to access {url}. Status Code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to access {url}: {e}")

def start_pinging():
    """
    Main function to run the pinger in a loop.
    """
    print(f"Starting website pinger for: {TARGET_URL}")
    print(f"Maximum delay between pings is {MAX_DELAY_MINUTES} minutes.")

    # Convert max delay to seconds for use with time.sleep()
    max_delay_seconds = MAX_DELAY_MINUTES * 60

    while True:
        # Step 1: Ping the website
        ping_website(TARGET_URL)
        
        # Step 2: Generate a random delay
        # We ensure a minimum delay of 1 second to avoid excessive requests.
        delay_seconds = random.randint(720, max_delay_seconds)
        
        print(f"Waiting for {delay_seconds} seconds before the next ping...")
        
        # Step 3: Wait for the random duration
        time.sleep(delay_seconds)

if __name__ == "__main__":
    start_pinging()
