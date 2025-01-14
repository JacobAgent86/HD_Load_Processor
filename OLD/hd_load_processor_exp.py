import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from tqdm import tqdm
import time


# Set up Selenium WebDriver
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=options)
    return driver

# Scrape data for a single SKU
# Scrape data for a single SKU
def scrape_sku(driver, sku):
    url = f"https://www.homedepot.com/s/{sku}"
    print(f"\nScraping SKU: {sku}")
    price_extraction_attempts = []  # Track all price extraction attempts for debugging

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Extract title
        try:
            title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
        except NoSuchElementException:
            title = "Title not found"
        except Exception as e:
            title = f"Error extracting title: {str(e)}"

        # Extract price
        price = "Price not found"
        try:
            # Attempt 1: Look for sticky-nav price
            sticky_nav_price = driver.find_element(By.CSS_SELECTOR, "[data-testid^='sticky-nav__price-value--']")
            if sticky_nav_price:
                price_text = sticky_nav_price.get_attribute("data-testid")
                price_match = re.search(r"sticky-nav__price-value--([\d.]+)", price_text)
                if price_match:
                    price = f"${price_match.group(1)}"
                    price_extraction_attempts.append(f"Price found using sticky-nav: {price}")
            
            # Attempt 2: Look for split span elements (dollar and cents split)
            if price == "Price not found":
                price_spans = driver.find_elements(By.CSS_SELECTOR, "span.sui-font-display")
                dollar_part, cents_part = None, None
                for span in price_spans:
                    text = span.text.strip()
                    price_extraction_attempts.append(f"Inspecting span: '{text}'")
                    if re.match(r"^\d+$", text):  # Likely the dollar part
                        dollar_part = text
                    elif re.match(r"^\d{2}$", text):  # Likely the cents part
                        cents_part = text
                    if dollar_part and cents_part:
                        price = f"${dollar_part}.{cents_part}"
                        price_extraction_attempts.append(f"Price constructed from spans: {price}")
                        break
            
            # Attempt 3: Check if the item is discontinued
            if price == "Price not found":
                try:
                    discontinued_element = driver.find_element(By.CSS_SELECTOR, ".discontinued__two-tile-header")
                    if "discontinued" in discontinued_element.text.lower():
                        price = "Item is discontinued"
                        price_extraction_attempts.append("Item marked as discontinued")
                except NoSuchElementException:
                    price_extraction_attempts.append("Item not marked as discontinued")
        
        except Exception as e:
            price_extraction_attempts.append(f"Error during price extraction: {str(e)}")
        
        # Compile validation status
        validation_status = []
        if "not found" in title.lower():
            validation_status.append("Title not found")
        if "not found" in price.lower():
            validation_status.append("Price not found")
        validation_status = "Valid" if not validation_status else "; ".join(validation_status)

        # Debugging output for price extraction
        print(f"\nPrice Extraction Debug for SKU {sku}:")
        for attempt in price_extraction_attempts:
            print(f"  - {attempt}")

        print(f"Validation Status for SKU {sku}: {validation_status} | Price: {price}")
        return [sku, url, validation_status, price, title]

    except Exception as e:
        print(f"Error scraping SKU {sku}: {str(e)}")
        return [sku, url, f"Invalid (Exception: {str(e)})", "Price not found", "Title not found"]


# Process data
def process_data(pasted_data):
    rows = []
    errors = []
    driver = setup_driver()

    lines = pasted_data.strip().split("\n")

    for line in tqdm(lines, desc="Processing SKUs", unit="SKU"):
        fields = line.split("\t")
        if len(fields) < 7:
            errors.append(f"Invalid input format: {line}")
            continue

        sku = fields[0]
        quantity = int(fields[5])  # Original quantity from input
        wholesale_price = float(fields[6].replace('$', '').replace(',', ''))

        result = scrape_sku(driver, sku)

        # Calculate Retail Price (Total)
        retail_price = float(result[3].replace('$', '')) if "$" in result[3] else 0.0
        retail_price_total = retail_price * quantity

        # Append row (quantity remains unchanged)
        row = result[:5] + [quantity, f"${wholesale_price / quantity:.2f}", f"${wholesale_price:.2f}", f"${retail_price_total:.2f}" if retail_price_total > 0 else "N/A"]
        rows.append(row)

    driver.quit()
    return rows, errors

# Save CSV file
def save_csv(rows):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"HD_Load_{timestamp}.csv"

    headers = [
        "SKU", "URL", "Validation Status", "Retail Price", "Title",
        "Quantity", "Wholesale Price Per Item", "Wholesale Price (Total)", "Retail Price (Total)"
    ]
    column_limit = len(headers)

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)  # Write headers

        for row in rows:
            writer.writerow(row[:column_limit])  # Trim to column limit

    print(f"CSV file saved as {filename}")

    # Save HTML files for specific SKUs
    while True:
        sku_to_save = input("Enter a SKU to save its HTML file (or press Enter to skip): ").strip()
        if not sku_to_save:
            break

        for row in rows:
            if row[0] == sku_to_save and len(row) > 5 and row[-1]:  # Check if page_source exists
                html_filename = f"SKU_{sku_to_save}_HTML_{timestamp}.html"
                with open(html_filename, 'w', encoding='utf-8') as htmlfile:
                    htmlfile.write(row[-1])
                print(f"HTML file saved as {html_filename}")
                break
        else:
            print(f"No data found for SKU {sku_to_save}.")

# Analyze data and print summary
def analyze_data(rows):
    total_quantity = 0
    total_wholesale = 0.0
    total_retail = 0.0
    valid_items = 0

    for row in rows:
        try:
            quantity = int(row[5])  # Ensure quantity remains original
            wholesale_price_total = float(row[7].replace('$', '')) if "$" in row[7] else 0.0
            retail_price_total = float(row[8].replace('$', '')) if "$" in row[8] else 0.0

            total_quantity += quantity
            total_wholesale += wholesale_price_total
            if retail_price_total > 0:
                total_retail += retail_price_total
                valid_items += quantity
        except Exception as e:
            print(f"Error processing row: {row}. Error: {e}")

    avg_retail = total_retail / valid_items if valid_items > 0 else 0.0

    print("\nData Summary:")
    print(f"Total Items (by Quantity): {total_quantity}")
    if total_quantity > 0:
        print(f"Invalid Items: {total_quantity - valid_items} ({(total_quantity - valid_items) / total_quantity * 100:.2f}%)")
    else:
        print("Invalid Items: 0 (0.00%)")
    print(f"Total Wholesale Price: ${total_wholesale:.2f}")
    print(f"Total Retail Price: ${total_retail:.2f}")
    print(f"Average Retail Price: ${avg_retail:.2f}")

# Main script
def main():
    def process_pasted_data(pasted_data):
        rows, errors = process_data(pasted_data)
        analyze_data(rows)

        if input("\nCreate CSV file? (y/n): ").strip().lower() == 'y':
            save_csv(rows)

        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(error)

    open_text_window(process_pasted_data)

# Tkinter text input
def open_text_window(callback):
    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    pasted_data = simpledialog.askstring("Input Data", "Paste your data here:")
    if pasted_data:
        callback(pasted_data)

if __name__ == "__main__":
    main()
