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

def check_chrome_installed():
    """Check if Google Chrome is installed and display an error popup if not."""
    chrome_path = (
        shutil.which("google-chrome") or
        shutil.which("chrome") or
        # Add standard installation paths for Windows
        r"C:\Program Files\Google\Chrome\Application\chrome.exe" if os.path.exists(r"C:\Program Files\Google\Chrome\Application\chrome.exe") else None or
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" if os.path.exists(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") else None or
        # Add standard installation paths for MacOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") else None or
        # Add standard installation paths for Linux
        "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None or
        "/usr/local/bin/google-chrome" if os.path.exists("/usr/local/bin/google-chrome") else None
    )

    if not chrome_path:
        # Create a Tkinter root and withdraw it to avoid showing an empty window
        root = Tk()
        root.withdraw()

        # Show an error message popup
        messagebox.showerror(
            "Chrome Not Installed",
            "Google Chrome is not installed on this system or is not in a standard location. "
            "Please install Google Chrome or ensure it is in the PATH and try again."
            "If you are seeing this message and do have Google Chrome installed, please email Jacob@Agent86.shop."
        )

        # Destroy the root and exit the program
        root.quit()
        root.destroy()
        sys.exit(1)

    print(f"Google Chrome found at: {chrome_path}")

import time
import re
import csv
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tkinter import Tk, simpledialog, Toplevel, Text, Button, Scrollbar
from tkinter import Label
from tkinter import messagebox
from tkinter.ttk import Progressbar
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger

# Suppress Selenium logs
selenium_logger.setLevel(logging.WARNING)


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
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    from tkinter.ttk import Progressbar

    def merge_duplicates(rows):
        """Merge duplicate SKUs by summing quantities and recalculating costs."""
        merged_data = {}

        for row in rows:
            sku = row[0]  # SKU is the key
            retail_price = float(row[1].replace("$", "")) if row[1] != "Price not found" else 0.0
            quantity = int(row[3])  # Convert quantity to integer
            cost_per_item = float(row[4].replace("$", "")) if row[4] != "N/A" else 0.0

            if sku in merged_data:
                # Update existing SKU
                merged_data[sku]['quantity'] += quantity
                merged_data[sku]['total_retail_value'] += retail_price * quantity
                merged_data[sku]['total_cost'] += quantity * cost_per_item
            else:
                # Add new SKU
                merged_data[sku] = {
                    'retail_price': retail_price,
                    'title': row[2],
                    'quantity': quantity,  # Store quantity as integer
                    'cost_per_item': cost_per_item,
                    'total_retail_value': retail_price * quantity,
                    'total_cost': quantity * cost_per_item,
                    'validity_status': row[5],
                    'url': row[6],
                }
            
            try:
                quantity = int(parts[-2])  # Parse quantity
            except ValueError:
                print(f"Invalid quantity in line: {line}")
                continue  # Skip this line

        # Convert merged data back to list format
        merged_rows = []
        for sku, data in merged_data.items():
            merged_rows.append([
                sku,
                f"${data['retail_price']:.2f}",
                f"${data['total_retail_value']:.2f}",
                data['title'],
                data['quantity'],  # Ensure quantity remains an integer
                f"${data['cost_per_item']:.2f}",
                f"${data['total_cost']:.2f}",
                data['validity_status'],
                data['url'],
            ])

        return merged_rows

    rows = []
    errors = []
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-software-rasterizer")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Shared data
    valid_data = []

    # Parse input lines
    lines = [line for line in pasted_data.strip().split("\n") if line.strip()]
    total_lines = len(lines)

    # Handle progress bar close button behavior
    def on_close():
        """Handle the user closing the progress bar window via the 'X' button."""
        print("Processing window closed by the user. Exiting program.")
        progress_window.quit()
        progress_window.destroy()
        driver.quit()
        sys.exit(0)  # Terminate the program

    # Create a progress bar window
    root = Tk()
    root.withdraw()
    progress_window = Toplevel(root)
    progress_window.title("Processing SKUs")
    progress_window.geometry("600x300")

    progress_window.protocol("WM_DELETE_WINDOW", on_close)

    progress_label = Label(progress_window, text=f"Processing 0 of {total_lines} SKUs...\nEstimated time remaining: Calculating...")
    progress_label.pack(pady=10)

    progress_bar = Progressbar(progress_window, orient="horizontal", length=400, mode="determinate")
    progress_bar.pack(pady=20)
    progress_bar["maximum"] = total_lines
    progress_bar["value"] = 0

    root.update()

    start_time = time.time()

    # Helper function to format time as MM:SS
    def format_time(seconds):
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s" if minutes > 0 else f"{remaining_seconds}s"

    try:
        for i, line in enumerate(lines):
            current_time = time.time()
            elapsed_time = current_time - start_time
            avg_time_per_sku = elapsed_time / (i + 1)
            remaining_time = avg_time_per_sku * (total_lines - (i + 1))

            # Format remaining time as MM:SS
            formatted_remaining_time = format_time(remaining_time)

            progress_label.config(
                text=(
                    f"Processing {i + 1} of {total_lines} SKUs...\n"
                    f"Estimated time remaining: {formatted_remaining_time}\n"
                    f"Average time per SKU: {avg_time_per_sku:.2f} seconds"
                )
            )
            root.update()

            parts = line.split("\t")
            if len(parts) < 6:
                # Handle incomplete lines
                sku = parts[0] if parts else "Unknown SKU"
                quantity = 1  # Default quantity
                wholesale_price = 0.0  # Default wholesale price
                result = scrape_sku(driver, sku, valid_data)
                rows.append([sku, result[3], result[4], quantity, f"${wholesale_price:.2f}", "Invalid", result[1]])
                progress_bar["value"] += 1
                root.update()
                continue

            sku = parts[0]
            try:
                quantity = int(parts[-2])
                wholesale_price = float(parts[-1].replace('$', '').replace(',', '')) * (wholesale_multiplier / 100)
            except ValueError as ve:
                errors.append(f"Invalid numeric value in line {i + 1}: {line}")
                progress_bar["value"] += 1
                root.update()
                continue

            result = scrape_sku(driver, sku, valid_data)
            rows.append([sku, result[3], result[4], quantity, f"${wholesale_price:.2f}", result[2], result[1]])

            if result[2] == "Valid":
                valid_data.append(result)

            progress_bar["value"] += 1
            root.update()

    except Exception as e:
        print(f"FATAL ERROR: Exception occurred: {str(e)}")
        errors.append(str(e))
    finally:
        progress_window.quit()
        progress_window.destroy()
        driver.quit()

    # Merge duplicate SKUs
    print(f"Rows before merging duplicates: {len(rows)}")  # Debug
    rows = merge_duplicates(rows)
    print(f"Rows after merging duplicates: {len(rows)}")  # Debug

    # Ensure all quantities are integers before returning
    for row in rows:
        row[3] = int(row[3]) if isinstance(row[3], str) and row[3].isdigit() else row[3]
        
    try:
        for i, line in enumerate(lines):
            parts = line.split("\t")
        
        # Validate the line structure
        if len(parts) < 6:
            print(f"Skipping malformed line {i + 1}: {line}")
            continue
        
        sku = parts[0].strip()
        try:
            quantity = int(parts[-2])
            wholesale_price = float(parts[-1].replace('$', '').replace(',', '')) * (wholesale_multiplier / 100)
        except ValueError:
            print(f"Invalid numeric values in line {i + 1}: {line}")
            continue

        result = scrape_sku(driver, sku, valid_data)
        row = [sku, result[3], result[4], quantity, f"${wholesale_price:.2f}", result[2], result[1]]
        
        # Debugging: Print row before adding
        print(f"Processed row: {row}")
        rows.append(row)

except Exception as e:
    print(f"FATAL ERROR: Exception occurred: {str(e)}")
    errors.append(str(e))

    return rows, errors

# Function to save data to CSV
def save_csv(rows):
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"HD_Load_Results_{current_time}.csv"
    file_path = os.path.join(os.getcwd(), filename)  # Full path to the file

    root = Tk()
    root.withdraw()

    # Create a popup window for Save/Don't Save
    save_window = Toplevel(root)
    save_window.title("Save CSV")
    save_window.geometry("400x150")

    # Handle close button behavior
    def on_close():
        """Handle the user closing the Save CSV window via the 'X' button."""
        print("Save CSV window closed by the user. Exiting program.")
        root.quit()
        root.destroy()
        sys.exit(0)  # Terminate the program

    save_window.protocol("WM_DELETE_WINDOW", on_close)

    # Label with the save prompt
    save_label = Label(save_window, text=f"Do you want to save the results to the file:\n'{filename}'?")
    save_label.pack(pady=10)

    def save_and_close():
        """Save the data to a CSV file and display a success popup."""
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
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
            for row in rows:
                sku = row[0]
                retail_price = float(row[1].replace("$", "")) if row[1] != "Price not found" else 0.0
                title = row[2]
                quantity = row[3]
                cost = float(row[4].replace("$", "")) if row[4] != "N/A" else 0.0
                validity_status = row[5]
                url = row[6]

                total_retail_value = f"${retail_price * quantity:.2f}" if retail_price > 0 else "N/A"
                cost_per_quantity = f"${cost / quantity:.2f}" if quantity > 0 else "N/A"

                writer.writerow([
                    sku,
                    row[1],
                    total_retail_value,
                    title,
                    quantity,
                    cost_per_quantity,
                    row[4],
                    validity_status,
                    url
                ])
        
        # Display success popup
        root = Tk()
        root.withdraw()
        messagebox.showinfo(
            "Save Successful",
            f"File '{filename}' was saved successfully to:\n{os.path.abspath(filename)}"
        )
        
        save_window.quit()
        save_window.destroy()
        sys.exit(0)  # Terminate the program

    def cancel_and_close():
        print("Save canceled.")
        save_window.quit()
        save_window.destroy()
        sys.exit(0)  # Terminate the program

    # Buttons for "Save" and "Don't Save"
    save_button = Button(save_window, text="Save", command=save_and_close)
    save_button.pack(side="left", padx=20, pady=10)

    cancel_button = Button(save_window, text="Don't Save", command=cancel_and_close)
    cancel_button.pack(side="right", padx=20, pady=10)

    save_window.mainloop()

# Function to analyze and display summary in a popup
def analyze_data(rows, start_time):
    if not rows:
        print("No data to analyze.")
        return
        
    for row in rows:
    if not isinstance(row[3], int):
        print(f"Row with invalid quantity: {row}")
        raise ValueError("Row contains invalid data for quantity.")

    total_quantity = sum(int(row[3]) for row in rows)
    total_lines = len(rows)
    valid_lines = sum(1 for row in rows if row[5] == "Valid")
    valid_percentage = 100 * valid_lines / total_lines if total_lines > 0 else 0
    total_wholesale = sum(float(row[4].replace('$', '')) for row in rows)
    total_retail = sum(float(row[1].replace("$", "")) * row[3] for row in rows if row[1] != "Price not found")
    avg_retail_price = (total_retail / total_quantity) if total_quantity > 0 else 0

    # Calculate total processing time
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    formatted_time = f"{minutes} minutes, {seconds} seconds" if minutes > 0 else f"{seconds} seconds"

    # Prepare summary text
    summary_text = (
    f"--- Summary ---\n"
    f"Total Quantity: {total_quantity}\n"
    f"Total Lines Input: {total_lines}\n"
    f"Valid Lines Output: {valid_lines} ({valid_percentage:.2f}%)\n"
    f"Total Adjusted Wholesale Price: ${total_wholesale:.2f}\n"
    f"Total Retail Price: ${total_retail:.2f}\n"
    f"Average Retail Price Per Item: ${avg_retail_price:.2f}\n"
    f"Total Processing Time: {formatted_time}\n"
    if total_quantity > 0
    else (
        f"--- Summary ---\n"
        f"Total Quantity: {total_quantity}\n"
        f"Total Lines Input: {total_lines}\n"
        f"Valid Lines Output: {valid_lines} ({valid_percentage:.2f}%)\n"
        f"Total Adjusted Wholesale Price: ${total_wholesale:.2f}\n"
        f"Total Retail Price: ${total_retail:.2f}\n"
        f"Average Retail Price Per Item: N/A\n"
        f"Total Processing Time: {formatted_time}\n"
    )
)

    root = Tk()
    root.withdraw()

    # Create summary popup
    summary_window = Toplevel(root)
    summary_window.title("Data Analysis Summary")
    summary_window.geometry("400x300")

    def close_and_trigger_save():
        """Handle 'X' button press by triggering Save CSV query."""
        print("Summary window closed by user. Triggering Save CSV query.")
        summary_window.quit()
        summary_window.destroy()
        save_csv(rows)  # Trigger the Save CSV query

    # Bind close button to trigger Save CSV query
    summary_window.protocol("WM_DELETE_WINDOW", close_and_trigger_save)

    # Text box to display summary
    text_box = Text(summary_window, wrap="word", height=15, width=50)
    text_box.insert("1.0", summary_text)
    text_box.config(state="disabled")  # Make the text box read-only
    text_box.pack(expand=True, fill="both")

    def close_summary():
        """Close the summary and trigger Save CSV query."""
        summary_window.quit()
        summary_window.destroy()
        save_csv(rows)

    # Close button
    close_button = Button(summary_window, text="Close", command=close_summary)
    close_button.pack(pady=10)

    summary_window.mainloop()

# Function to open text window
def open_text_window(callback):
    root = Tk()
    root.withdraw()

    # Input for wholesale multiplier
    multiplier = simpledialog.askfloat(
        "Input", 
        "Enter the percentage multiplier for wholesale price (e.g., 17.8 for 17.8%):"
    )
    if multiplier is None:
        print("No multiplier entered. Exiting.")
        return

    def on_submit():
        try:
            nonlocal pasted_data
            pasted_data = text_box.get("1.0", "end").strip()

            # Check if the input is empty
            if not pasted_data:
                messagebox.showwarning(
                    "No Data Submitted", 
                    "No data was submitted. Please paste data and try again."
                )
                return  # Stay on the popup

            window.quit()
            window.destroy()
        except Exception as e:
            print(f"Error in on_submit: {e}")

    def on_close():
        """Handle the user closing the window via the 'X' button."""
        print("Submit Info window closed by the user. Exiting program.")
        root.quit()  # Quit the entire Tkinter event loop
        root.destroy()  # Destroy the root window
        sys.exit(0)  # Terminate the program

    # Larger window for text input
    pasted_data = ""  # Initialize pasted_data variable
    window = Toplevel(root)
    window.title("Paste Your Data")
    window.geometry("800x600")

    # Bind the 'X' button (window close) to the on_close function
    window.protocol("WM_DELETE_WINDOW", on_close)

    text_box = Text(window, wrap="none")
    text_box.pack(expand=True, fill="both")

    submit_button = Button(window, text="Submit", command=on_submit)
    submit_button.pack()

    window.mainloop()

    if pasted_data:
        callback(pasted_data, multiplier)

# Main function
def main():
    def process_pasted_data(pasted_data, multiplier):
        start_time = time.time()  # Start timer for processing
        rows, errors = process_data(pasted_data, multiplier)  # Process the data

        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(error)

        if rows:
            analyze_data(rows, start_time)  # Pass start_time to analyze_data
            save_csv(rows)  # Prompt to save the CSV after analysis

    open_text_window(process_pasted_data)

if __name__ == "__main__":
    check_chrome_installed()
    main()

