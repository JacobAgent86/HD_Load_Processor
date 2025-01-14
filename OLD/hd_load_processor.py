#pyinstaller --clean --onefile hd_load_processor.py

import subprocess
import sys
from importlib.metadata import distributions

def install_missing_packages():
    REQUIRED_PACKAGES = [
        "selenium",
        "tqdm",
        "webdriver-manager"
    ]

    for package in REQUIRED_PACKAGES:
        try:
            # Handle special cases where the import name doesn't match the PyPI package name
            import_name = package.replace("-", "_")
            __import__(import_name)  # Try importing the package
            #print(f"DEBUG: Package '{package}' is already installed.")
        except ImportError:
            #print(f"DEBUG: Package '{package}' not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
            #print(f"DEBUG: Package '{package}' successfully installed.")

# Call the function to install missing packages
install_missing_packages()

import time
import re
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tkinter import Tk, simpledialog, Toplevel, Text, Button, Scrollbar
from datetime import datetime
from tqdm import tqdm

# Redundancy check for duplicate SKUs
def check_duplicate_sku(sku, valid_data):
    for row in valid_data:
        if row[0] == sku and row[2] == "Valid":
            #print(f"DEBUG: Duplicate SKU found: {sku} | Copying valid price and title.")
            return row[3], row[4]
    return None, None

# Main scrape_sku function with Normal Page Load only
def scrape_sku(driver, sku, valid_data):
    url = f"https://www.homedepot.com/s/{sku}"
    #print(f"DEBUG: Scraping SKU: {sku} | URL: {url}")
    result = {
        "price": "Price not found",
        "title": "Title not found"
    }
    discontinued = False

    try:
        # Check for duplicates before processing
        price, title = check_duplicate_sku(sku, valid_data)
        if price and title:
            #print(f"DEBUG: SKU {sku} already has valid data: Price = {price}, Title = {title}")
            return [sku, url, "Valid", price, title]

        # Step 1: Load the page
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        #print(f"DEBUG: Page loaded successfully for SKU {sku}")
        #time.sleep(2)  # Allow for dynamic content to load (Enable for potentially more accurate results)
        
        # Stop loading further content after detecting critical elements
        driver.execute_script("window.stop();")

        # Step 2: Detect discontinued items
        discontinued_element = driver.find_elements(By.XPATH, "//div[@class='discontinued__two-tile-header' and text()='This Item is Discontinued']")
        if discontinued_element:
            result["price"] = "$0.00"
            discontinued = True
            #print(f"DEBUG: Item {sku} is marked as discontinued. Price set to $0.00.")
        
        # Step 3: Extract price (skip if discontinued)
        if not discontinued:
            # Extract price (using regex)
            price_match = re.search(r'\"value\":([\d.]+),', driver.page_source)
            if price_match:
                result["price"] = f"${float(price_match.group(1)):.2f}"
                #print(f"DEBUG: Price found for SKU {sku}: {result['price']}")
            else:
                #print(f"DEBUG: Price not found for SKU {sku}.")
                result["price"] = "Price not found"

        # Step 4: Extract brand name and title
        brand_match = re.search(r'\"brandName\":\"(.*?)\"', driver.page_source)
        title_match = re.search(r'\"productLabel\":\"(.*?)\"', driver.page_source)

        if title_match:
            result["title"] = title_match.group(1)
            if brand_match:
                brand_name = brand_match.group(1)
                result["title"] = f"{brand_name} {result['title']}"
                #print(f"DEBUG: Brand and Title combined for SKU {sku}: {result['title']}")
            else:
                #print(f"DEBUG: Title found for SKU {sku}: {result['title']}")
                result["title"] = title_match.group(1)
        else:
            #print(f"DEBUG: Title not found for SKU {sku}.")
            result["title"] = "Title not found"


    except Exception as e:
        print(f"Error scraping SKU {sku}: {str(e)}")

    # Validation Status
    validation_status = "Valid" if result["price"] != "Price not found" and result["title"] != "Title not found" else "Invalid"
    #print(f"DEBUG: Final Status for SKU {sku}: {validation_status} | Price: {result['price']} | Title: {result['title']}")
    
    return [
    sku,                # result[0]
    url,                # result[1]
    validation_status,  # result[2]
    result["price"],    # result[3]
    result["title"]     # result[4]
]

# Function to process data
def process_data(pasted_data, wholesale_multiplier):
    #print(f"DEBUG: Entered Process Data Function")
    
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    
    rows = []
    errors = []
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode to prevent opening a browser window
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-webgl")  # Disable WebGL
    options.add_argument("--disable-software-rasterizer")  # Prevent software fallback
    options.add_argument("--disable-extensions")  # Disable Chrome extensions
    options.add_argument("--disable-3d-apis")  # Disable 3D APIs
    options.add_argument("--log-level=3")  # Suppress logging
    options.add_argument("--disable-logging")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Disable JavaScript execution (Optional, may impact data extraction)
    options.add_argument("--disable-javascript")

    # Disable images to speed up page loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    valid_data = []

    try:
        lines = [line for line in pasted_data.strip().split("\n") if line.strip()]
        #print(f"DEBUG: Total input lines after cleanup: {len(lines)}")

        for i, line in enumerate(tqdm(lines, desc="Processing SKUs", unit="SKU")):
            #print(f"DEBUG: Processing line {i + 1}: {repr(line)}")

            parts = line.split("\t")
            #print(f"DEBUG: Split line into parts: {parts}")
            
            if len(parts) < 6:
                errors.append(f"Invalid data format in line {i + 1}: {line}")
                print(f"ERROR: Line {i + 1} has insufficient parts: {repr(parts)}")
                continue

            sku = parts[0]
            #print(f"DEBUG: Extracted SKU: {sku}")
            try:
                quantity = int(parts[-2])
                wholesale_price = float(parts[-1].replace('$', '').replace(',', '')) * (wholesale_multiplier / 100)
                #print(f"DEBUG: Parsed Quantity: {quantity}, Adjusted Wholesale Price: {wholesale_price:.2f}")
            except ValueError as ve:
                errors.append(f"Invalid numeric value in line {i + 1}: {line}")
                print(f"ERROR: Line {i + 1} has invalid numeric values: {str(ve)}")
                continue

            result = scrape_sku(driver, sku, valid_data)
            rows.append([sku, result[3], result[4], quantity, f"${wholesale_price:.2f}", result[2], result[1]])

            if result[2] == "Valid":
                valid_data.append(result)

    except Exception as e:
        print(f"FATAL ERROR: Exception occurred: {str(e)}")
        errors.append(str(e))
    finally:
        driver.quit()
        #print(f"DEBUG: Selenium driver successfully quit.")

    for row in rows:
        if row[1] == "Price not found" or row[2] == "Title not found":
            price, title = check_duplicate_sku(row[0], valid_data)
            if price and title:
                row[1] = price
                row[2] = title
                row[5] = "Valid"
                #print(f"DEBUG: Fixing invalid SKU {row[0]} using valid duplicate data.")

    #print(f"DEBUG: Total processed rows: {len(rows)}")
    #print(f"DEBUG: Total errors encountered: {len(errors)}")
    return rows, errors

# Function to save data to CSV
def save_csv(rows):
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"HD_Load_Results_{current_time}.csv"
    print(f"\nSave results to {filename}? (Y/N): ", end="")
    choice = input().strip().lower()
    if choice == 'y':
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            # Updated headers with new columns
            writer.writerow([
                "SKU",
                "Retail Price",
                "Total Retail Value",
                "Title",
                "Quantity",
                "Cost per Item",
                "Total Cost",
                "Validity Status",
                "URL"
            ])
            # Add logic for new columns when writing rows
            for row in rows:
                retail_price = float(row[1].replace("$", "")) if row[1] != "Price not found" else 0.0
                total_retail_value = f"${retail_price * quantity:.2f}" if retail_price > 0 else "N/A"
                quantity = row[3]
                cost = float(row[4].replace("$", "")) if row[4] != "N/A" else 0.0
                cost_per_quantity = f"${cost / quantity:.2f}" if quantity > 0 else "N/A"
                writer.writerow(row[:5] + [cost_per_quantity, total_retail_value] + row[5:])
        print(f"Results saved to {filename}")
    else:
        print("Save canceled.")


# Function to analyze and print summary
def analyze_data(rows):
    if not rows:
        print("No data to analyze.")
        return

    total_quantity = sum(row[3] for row in rows)
    total_lines = len(rows)
    valid_lines = sum(1 for row in rows if row[5] == "Valid")
    valid_percentage = 100 * valid_lines / total_lines if total_lines > 0 else 0
    total_wholesale = sum(float(row[4].replace('$', '')) for row in rows)
    total_retail = sum(float(row[1].replace("$", "")) * row[3] for row in rows if row[1] != "Price not found")

    print("\n--- Summary ---")
    print(f"Total Quantity: {total_quantity}")
    print(f"Total Lines Input: {total_lines}")
    print(f"Valid Lines Output: {valid_lines} ({valid_percentage:.2f}%)")
    print(f"Total Adjusted Wholesale Price: ${total_wholesale:.2f}")
    print(f"Total Retail Price: ${total_retail:.2f}")
    print(f"Average Retail Price Per Item: ${total_retail / total_quantity:.2f}" if total_quantity > 0 else "Average Retail Price: N/A")

# Function to open text window
def open_text_window(callback):
    #print(f"DEBUG: Entered Text Window Function")
    root = Tk()
    root.withdraw()
    
    # Input for wholesale multiplier
    multiplier = simpledialog.askfloat("Input", "Enter the percentage multiplier for wholesale price (e.g., 17.8 for 17.8%):")
    if multiplier is None:
        print("No multiplier entered. Exiting.")
        return

    # Larger window for text input
    pasted_data = ""  # Initialize pasted_data variable

    def on_submit():
        try:
            #print(f"DEBUG: on_submit called")
            nonlocal pasted_data
            pasted_data = text_box.get("1.0", "end").strip()
            #print(f"DEBUG: Pasted data length: {len(pasted_data)}")
            window.quit()
            window.destroy()
            #print(f"DEBUG: window.quit() and window.destroy() called")
        except Exception as e:
            print(f"Error in on_submit: {e}")
    
    window = Toplevel(root)
    window.title("Paste Your Data")
    window.geometry("800x600")

    text_box = Text(window, wrap="none")
    text_box.pack(expand=True, fill="both")
    
    submit_button = Button(window, text="Submit", command=on_submit)
    submit_button.pack()
    #print(f"DEBUG: window.mainloop() Entered")
    window.mainloop()
    #print(f"DEBUG: window.mainloop() Passed")
    callback(pasted_data, multiplier)

# Main function
def main():
    def process_pasted_data(pasted_data, multiplier):
        rows, errors = process_data(pasted_data, multiplier)
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(error)
        if rows:
            analyze_data(rows)
            save_csv(rows)

    open_text_window(process_pasted_data)

if __name__ == "__main__":
    main()

