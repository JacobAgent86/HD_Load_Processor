import requests
from bs4 import BeautifulSoup
import os
import re
import time  # Import the time module for sleep

# Create a folder to store the images
folder = 'ebay_images'
if not os.path.exists(folder):
    os.makedirs(folder)

# List of eBay item URLs and their corresponding item numbers
ebay_links = [
    "https://www.ebay.com/itm/155918237140",  # Example item
    # Add more eBay item URLs here
]

item_numbers = [
    677,  # Corresponding item number for the first link
    # Add more item numbers here, matching the order of ebay_links
]

# Function to download images from a specific eBay item URL
def download_images(ebay_url, item_number):
    # Send a GET request to fetch the page content
    response = requests.get(ebay_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all image URLs in the page
    img_tags = soup.find_all('img', {'src': re.compile('^https://i.ebayimg.com')})
    
    # Filter out unwanted images like banners, logos, and related items
    img_urls = []
    for img in img_tags:
        img_url = img.get('src')
        if img_url:
            # Skip banners, logos, or other related images
            if '/cr/v/c01/' in img_url or '/00/' in img_url or 's-l64' in img_url:
                print(f"Skipping banner, logo, or related image: {img_url}")
                continue

            # Only add item images that have a high resolution (s-l1600)
            if 's-l1600' in img_url:
                img_urls.append(img_url)
            elif 's-l500' in img_url or 's-l140' in img_url:
                # Convert lower-resolution images to high resolution if possible
                high_res_url = img_url.replace("s-l140", "s-l1600").replace("s-l500", "s-l1600")
                img_urls.append(high_res_url)

    # Now that we have a list of high-resolution image URLs, apply the new skip logic
    i = 0
    while i < len(img_urls):
        img_url = img_urls[i]
        if 'thumbs' in img_url:  # If the current image link starts with "https://i.ebayimg.com/thumbs"
            print(f"Skipping image {i + 1}: {img_url}")
            i += 3  # Skip this image and the next two images
        else:
            # Proceed to download the image
            print(f"Downloading image {i + 1} from {img_url}")
            img_data = requests.get(img_url).content
            img_name = f"{folder}/{item_number}-{i + 1}.jpg"  # Custom naming based on item number
            with open(img_name, 'wb') as f:
                f.write(img_data)
            print(f"Downloaded {img_name}")
            i += 1  # Move to the next image

        # Add a 1-second delay between downloads
        time.sleep(1)

# Loop over each eBay item link and download the images
for ebay_url, item_number in zip(ebay_links, item_numbers):
    print(f"Processing item {item_number} from {ebay_url}")
    download_images(ebay_url, item_number)
