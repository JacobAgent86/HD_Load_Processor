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
"https://www.ebay.com/itm/166602347537",
"https://www.ebay.com/itm/166603548304",
"https://www.ebay.com/itm/156071297418",
"https://www.ebay.com/itm/166606471381",
"https://www.ebay.com/itm/156073427962",
"https://www.ebay.com/itm/166608440773",
"https://www.ebay.com/itm/156078407253",
"https://www.ebay.com/itm/156089840814",
"https://www.ebay.com/itm/156090238888",
"https://www.ebay.com/itm/156103255309",
"https://www.ebay.com/itm/166635405212",
"https://www.ebay.com/itm/156105091463",
"https://www.ebay.com/itm/156105111507",
"https://www.ebay.com/itm/166637490832",
"https://www.ebay.com/itm/156107397232",
"https://www.ebay.com/itm/166637659346",
"https://www.ebay.com/itm/166637778927",
"https://www.ebay.com/itm/156112057257",
"https://www.ebay.com/itm/156112186937",
"https://www.ebay.com/itm/156116253568",
"https://www.ebay.com/itm/156120124454",
"https://www.ebay.com/itm/166664404574",
"https://www.ebay.com/itm/166674119917",
"https://www.ebay.com/itm/166683813691",
"https://www.ebay.com/itm/166693992626",
"https://www.ebay.com/itm/166694433004",
"https://www.ebay.com/itm/156345892805",
"https://www.ebay.com/itm/166916080182",
"https://www.ebay.com/itm/156356131002",
"https://www.ebay.com/itm/166919531280",
"https://www.ebay.com/itm/156371060442",
"https://www.ebay.com/itm/166934101989",
"https://www.ebay.com/itm/166954904448",
"https://www.ebay.com/itm/156391440227",
"https://www.ebay.com/itm/156403114506",
"https://www.ebay.com/itm/166966636852",
"https://www.ebay.com/itm/156403114505",
"https://www.ebay.com/itm/166966636855",
"https://www.ebay.com/itm/166966636860",
"https://www.ebay.com/itm/156403639603",
"https://www.ebay.com/itm/166980593127",
"https://www.ebay.com/itm/156419306948",
"https://www.ebay.com/itm/156440670809",
"https://www.ebay.com/itm/167018137444",
"https://www.ebay.com/itm/166340860477",
"https://www.ebay.com/itm/166548516585",
"https://www.ebay.com/itm/166017967892",
"https://www.ebay.com/itm/155498692064",
"https://www.ebay.com/itm/155514870126",
"https://www.ebay.com/itm/155522882023",
"https://www.ebay.com/itm/166350048417",
"https://www.ebay.com/itm/155808808680",
"https://www.ebay.com/itm/166360663583",
"https://www.ebay.com/itm/155810674395",
"https://www.ebay.com/itm/166362304008",
"https://www.ebay.com/itm/166362320875",
"https://www.ebay.com/itm/166363700198",
"https://www.ebay.com/itm/155812611784",
"https://www.ebay.com/itm/166363944546",
"https://www.ebay.com/itm/155835978865",
"https://www.ebay.com/itm/166430251546",
"https://www.ebay.com/itm/166481252793",
"https://www.ebay.com/itm/155952233571",
"https://www.ebay.com/itm/155961851956",
"https://www.ebay.com/itm/155965368659",
"https://www.ebay.com/itm/166662346994",
"https://www.ebay.com/itm/156003863214",
"https://www.ebay.com/itm/156088117798",
"https://www.ebay.com/itm/166909883366",
"https://www.ebay.com/itm/156345892804",
"https://www.ebay.com/itm/156399932051",
"https://www.ebay.com/itm/167000597538",
"https://www.ebay.com/itm/167030456721",
"https://www.ebay.com/itm/155759685943",
"https://www.ebay.com/itm/166319114666",
"https://www.ebay.com/itm/166319116695",
"https://www.ebay.com/itm/166319126881",
"https://www.ebay.com/itm/155950455857",
"https://www.ebay.com/itm/155950455848",
"https://www.ebay.com/itm/155950455861",
"https://www.ebay.com/itm/155950455856",
"https://www.ebay.com/itm/155950455852",
"https://www.ebay.com/itm/155950455859",
"https://www.ebay.com/itm/166319490968",
"https://www.ebay.com/itm/155772690503",
"https://www.ebay.com/itm/155772819076",
"https://www.ebay.com/itm/166330863552",
"https://www.ebay.com/itm/166340860571",
"https://www.ebay.com/itm/166415555396",
"https://www.ebay.com/itm/166438258547",
"https://www.ebay.com/itm/166465093054",
"https://www.ebay.com/itm/156035391254",
"https://www.ebay.com/itm/166591411366",
"https://www.ebay.com/itm/166596230703",
"https://www.ebay.com/itm/166596241625",
"https://www.ebay.com/itm/166917886561",
"https://www.ebay.com/itm/156393231773",
"https://www.ebay.com/itm/166956579838",
"https://www.ebay.com/itm/156406828930",
"https://www.ebay.com/itm/166978677921",
"https://www.ebay.com/itm/156429263971",
"https://www.ebay.com/itm/156429263961",
"https://www.ebay.com/itm/166993702592",
"https://www.ebay.com/itm/167000597537",
"https://www.ebay.com/itm/167002220129",
"https://www.ebay.com/itm/167004081814",
"https://www.ebay.com/itm/167030456723",
"https://www.ebay.com/itm/156470499713",
"https://www.ebay.com/itm/167038033330",
"https://www.ebay.com/itm/167041898533",
"https://www.ebay.com/itm/156473525185",
"https://www.ebay.com/itm/167044119456",
"https://www.ebay.com/itm/155782295446",
]

item_numbers = [
1144,
1148,
1158,
1159,
1170,
1171,
1182,
1219,
1226,
1246,
1251,
1254,
1255,
1266,
1269,
1270,
1272,
1278,
1281,
1288,
1306,
1346,
1362,
1385,
1402,
1407,
1535,
1536,
1552,
1555,
1556,
1557,
1564,
1566,
1603,
1604,
1605,
1606,
1609,
1628,
1657,
1663,
1728,
1766,
860135,
865213,
865242,
865284,
865405,
865436,
304,
351,
356,
373,
377,
379,
385,
393,
394,
508,
587,
715,
766,
789,
794,
890,
892,
1216,
1533,
1534,
1593,
1707,
1785,
860004,
860007,
860008,
860009,
860014,
860015,
860016,
860017,
860018,
860019,
860025,
860106,
860107,
860115,
860133,
559,
605,
659,
1019,
1104,
1107,
1112,
1547,
1573,
1576,
1643,
1651,
1690,
1691,
1697,
1706,
1712,
1723,
1786,
1791,
1792,
1802,
1803,
1807,
860006,
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
