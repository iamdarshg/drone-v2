#!/usr/bin/env python3
"""
KiCAD BOM Pricer - Automatically adds pricing information from Mouser API

Usage:
    python bom_pricer.py input_bom.csv [output_bom.csv]

Requirements:
    - Python 3.x
    - requests library (pip install requests)
    - Mouser API key as environment variable MOUSER_API_KEY

Input CSV format (KiCAD standard):
    Reference,Value,Footprint,Datasheet,Description,Vendor,MPN

Output CSV adds:
    Unit_Price,Extended_Price,Mouser_Part_Number,Packaging,Status
"""

import os
import sys
import csv
import time
import requests
from typing import Dict, List, Optional, Tuple

# Mouser API Configuration
MOUSER_API_BASE = "https://api.mouser.com/api/v2"
MOUSER_API_KEY = "f06458b2-0449-4d35-a930-1132e8a39099"

if not MOUSER_API_KEY:
    raise EnvironmentError("Mouser API key not found. Please set MOUSER_API_KEY environment variable.")

class MouserAPI:
    """Wrapper for Mouser API operations"""

    @staticmethod
    def search_by_part_number(part_number: str) -> Optional[Dict]:
        """Search Mouser by exact part number"""
        if not part_number.strip():
            return None

        url = f"{MOUSER_API_BASE}/search/partnumber"
        headers = {
            "Authorization": f"Bearer {MOUSER_API_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "partNumber": part_number,
            "searchOptions": "exact"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("Errors"):
                print(f"API Error for {part_number}: {data['Errors']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            print(f"Request failed for {part_number}: {str(e)}")
            return None

    @staticmethod
    def search_by_keyword(keyword: str) -> Optional[Dict]:
        """Search Mouser by keyword"""
        if not keyword.strip():
            return None

        # Try the correct Mouser API v2 endpoint
        url = "https://api.mouser.com/api/v2.0/search/keyword"
        headers = {
            "Authorization": f"Bearer {MOUSER_API_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "keyword": keyword,
            "records": 50  # Get more results for filtering
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("Errors"):
                print(f"API Error for keyword '{keyword}': {data['Errors']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            print(f"Request failed for keyword '{keyword}': {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.content}")
            else:
                print("No response received")
            return None

def filter_results(results: List[Dict]) -> Optional[Dict]:
    """Filter results to find best match based on packaging and price"""
    if not results:
        return None

    # Filter for cut tape or tray packaging
    filtered = []
    for result in results:
        packaging = result.get("Packaging", "").lower()
        if "cut tape" in packaging or "tray" in packaging:
            filtered.append(result)

    if not filtered:
        # If no cut tape/tray, use all results
        filtered = results

    # Find the cheapest option
    best_match = min(filtered, key=lambda x: float(x.get("PriceBreaks", [{}])[0].get("Price", float('inf'))))
    return best_match

def get_part_price(part_number: str, value: str) -> Tuple[Optional[float], str, str, str]:
    """
    Get price for a part using keyword search strategy:
    1. Always use keyword search using Value field
    2. Filter results for cut tape/tray packaging
    3. Select cheapest option

    Returns: (unit_price, mouser_part_number, packaging, status)
    """
    # Skip if no value to search
    if not value.strip():
        return None, "", "", "No Value to search"

    # Handle connector replacements
    search_value = value
    if value.startswith("Conn_"):
        # Replace connector patterns
        search_value = "2.54mm pitch male header"
        # For future: replace height/width with R rows and R*L pins
        # This would require additional parsing of the original value

    # Always use keyword search using processed Value field
    result = MouserAPI.search_by_keyword(search_value)
    status = "Found by Value keyword"

    if result and result.get("SearchResults"):
        parts = result["SearchResults"].get("Parts", [])
        if parts:
            best_part = filter_results(parts)
            if best_part:
                price_breaks = best_part.get("PriceBreaks", [])
                if price_breaks:
                    unit_price = float(price_breaks[0].get("Price", 0))
                    mouser_pn = best_part.get("MouserPartNumber", "")
                    packaging = best_part.get("Packaging", "")
                    return unit_price, mouser_pn, packaging, status

    # Not found
    return None, "", "", "Not found"

def process_bom(input_file: str, output_file: str) -> None:
    """Process BOM file and add pricing information"""
    print(f"Processing BOM: {input_file}")

    with open(input_file, mode='r', encoding='utf-8-sig') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames or []

        # Add new columns
        new_fieldnames = list(fieldnames) + [
            "Unit_Price",
            "Extended_Price",
            "Mouser_Part_Number",
            "Packaging",
            "Status"
        ]

        # Read all rows
        rows = list(reader)

    # Process each row
    processed_rows = []
    for i, row in enumerate(rows, 1):
        print(f"Processing row {i}/{len(rows)}: {row.get('Reference', 'N/A')}")

        # Get quantity - handle both Reference and Qty columns
        quantity = 1
        if 'Qty' in row and row['Qty'].strip():
            quantity = int(row['Qty'])
        else:
            # Parse from Reference field (e.g., "R1, R2, R3" = 3)
            quantity = len([r.strip() for r in row.get('Reference', '').split(',') if r.strip()])

        # Get MPN from row - handle different BOM formats
        mpn = ""
        if 'MPN' in row:
            mpn = row.get('MPN', '').strip()
        else:
            # For BOMs where Value contains the part number
            mpn = row.get('Value', '').strip()

        value = row.get('Value', '').strip()

        # Get price information
        unit_price, mouser_pn, packaging, status = get_part_price(mpn, value)

        # Calculate extended price
        extended_price = unit_price * quantity if unit_price else None

        # Update row
        row["Unit_Price"] = f"${unit_price:.2f}" if unit_price else "N/A"
        row["Extended_Price"] = f"${extended_price:.2f}" if extended_price else "N/A"
        row["Mouser_Part_Number"] = mouser_pn
        row["Packaging"] = packaging
        row["Status"] = status

        processed_rows.append(row)

        # Rate limiting - Mouser API has limits
        if i % 10 == 0:
            time.sleep(1)  # 1 second delay every 10 requests

    # Write output file
    with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)

    print(f"BOM processing complete. Output saved to: {output_file}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python bom_pricer.py input_bom.csv [output_bom.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "bom_with_prices.csv"

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)

    try:
        process_bom(input_file, output_file)
    except Exception as e:
        print(f"Error processing BOM: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
