# KiCAD BOM Pricer

Automatically adds pricing information from Mouser API to KiCAD-generated BOM files.

## Features

- **Exact MPN Search**: First tries to find parts by exact Manufacturer Part Number
- **Keyword Fallback**: If MPN not found, searches using the Value field
- **Smart Filtering**: Prefers cut tape or tray packaging when available
- **Cost Optimization**: Selects the cheapest option from filtered results
- **Quantity Calculation**: Calculates extended prices based on component quantities
- **Rate Limiting**: Built-in delays to respect Mouser API limits

## Requirements

- Python 3.x
- `requests` library (`pip install requests`)
- Mouser API key (free tier available)

## Setup

1. Install dependencies:
   ```bash
   pip install requests
   ```

2. Set your Mouser API key as an environment variable:
   ```bash
   # Windows
   set MOUSER_API_KEY=your_api_key_here

   # Linux/Mac
   export MOUSER_API_KEY=your_api_key_here
   ```

## Usage

```bash
python bom_pricer.py input_bom.csv [output_bom.csv]
```

- `input_bom.csv`: Your KiCAD-generated BOM file
- `output_bom.csv`: Output file with pricing (defaults to `bom_with_prices.csv`)

## Input Format

The script expects a standard KiCAD BOM CSV with these columns:
- **Reference**: Component references (e.g., "R1, R2, R3")
- **Value**: Component value (used for keyword search if MPN fails)
- **Footprint**: Component footprint
- **Datasheet**: Datasheet URL
- **Description**: Component description
- **Vendor**: Manufacturer name
- **MPN**: Manufacturer Part Number (primary search key)

## Output Format

The output CSV adds these columns:
- **Unit_Price**: Price per unit (USD)
- **Extended_Price**: Total price for quantity (Unit_Price × Quantity)
- **Mouser_Part_Number**: Mouser's part number
- **Packaging**: Package type (cut tape, tray, etc.)
- **Status**: How the part was found ("Found by MPN", "Found by Value keyword", "Not found")

## Example

```bash
python bom_pricer.py sample_bom.csv priced_bom.csv
```

## Notes

- The script handles API rate limits with automatic delays
- Parts not found on Mouser will show "N/A" for pricing
- For best results, ensure your BOM has accurate MPN information
- Mouser API free tier has ~1000 calls/day limit

## Troubleshooting

- **API Key Issues**: Ensure `MOUSER_API_KEY` is set correctly
- **Network Errors**: Check your internet connection
- **Rate Limits**: Reduce BOM size or wait for API limits to reset
- **Part Not Found**: Verify MPN accuracy or try manual search on Mouser
