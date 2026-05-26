# actual-amazon-noter

> **⚡ Web Uploader & Structural Split Transactions Fork**
>
> This fork extends the original `actual-amazon-noter` script to move beyond manual local execution and simple text tagging, offering robust structural transaction splitting and a premium centralized web interface.
>
> ### ✨ Key Fork Enhancements:
> * 🔗 **Structural Split Transactions**: Multi-item Amazon orders are automatically split into structural sub-transactions in your Actual Budget UI, pre-filled with correct individual product prices and notes.
> * 🌐 **Premium Web Companion (GUI)**: Deploys a gorgeous glassmorphism web dashboard featuring a drag-and-drop CSV uploader, execution/dry-run controls, in-cluster diagnostics, and a live-streaming dark terminal logs viewer.
> * 💷 **UK & Multi-Currency Support**: Dynamically detects purchase currency (such as GBP or EUR) from your Amazon data export, rather than defaulting to hardcoded USD.
> * 📦 **Docker & In-Cluster Orchestration**: Built to be containerized and securely deployed node-independently behind Traefik Basic Auth inside K3s/Kubernetes.

A Python script to update the "notes" field of records in Actual Budget with Amazon purchase details.

## Overview

This tool correlates Amazon transaction records from CSV exports with transactions in Actual Budget, then updates the Notes field with Amazon order details including:
- Amazon Order ID
- Order Date
- Product Name
- Shipping Address

The correlation looks:
- Transactions where the Payee, Imported_Payee, or Notes contains "Amazon"
AND
- Transactions within the date window where the billed cost matches the cost of the Amazon order 

A single transaction in Actual Budget for an Amazon purchase may correspond to multiple lines in the Amazon order history, as an Amazon purchase may be fulfilled by multiple vendors. This program will sum up the cost of each line item in the order history that shares a common Order Id. If a match is found with an Actual Budget transaction, the Notes field is updated with enough detail to allow the transaction to be split between multiple budgets.

As of **v2.0.0**, the script also natively utilizes Actual Budget's Split Transactions feature via the REST API. If a multi-item order is detected, it converts the parent transaction into a structural split (`is_parent: true`) and creates individual sub-transactions (`is_child: true`) with exact amounts, inherited payees, and corresponding notes for each individual Amazon product. It correctly balances the sub-transactions to ensure they sum perfectly to the parent total.

For example, if the Amazon Order_History.csv file contained (highly simplified):
```
    Order ID,Description,Cost
    12345,Orange juice,$1.99
    12345,3/4HP Ryobi Router,$59.99
    12345,CISCO 1900 Router,$95.00
```

This would be consider a single purchase of $156.98. If this matched a transaction in Actual Budget, the Notes field would be updated to include the tags:
```
    #Amazon-Order 12345
    #Amazon-Product-Name-Split-1 Orange juice #Amazon-Product-Cost-Split-1 $1.99
    #Amazon-Product-Name-Split-2 3/4HP Ryobi Router #Amazon-Product-Cost-Split-2 $59.99
    #Amazon-Product-Name-Split-3 CISCO 1900 Router #Amazon-Product-Cost-Split-3 $95.00
```
(all as a single line, appended to the existing Notes data). The script dynamically detects the currency from your Amazon CSV (defaulting to GBP instead of hardcoded USD).

In addition to updating the notes, **the transaction will structurally become a split transaction** with three sub-transactions in your Actual Budget UI, each pre-filled with the item's cost and product name, leaving the categories empty for you to classify manually.

This allows the transaction in Actual Budget to be split between different categories (groceries, woodworking, computing).

**Marketplace Orders:** The script now checks for `Amz` substrings as well as `Amazon`, which natively catches `Amznmktplace` (Amazon Marketplace) orders. Marketplace purchases are frequently fulfilled by multiple vendors in a single transaction, making the split transaction feature particularly useful here.

---

## 🌐 Web Companion Interface (GUI)

The project includes a **premium, glassmorphic Web Companion GUI** (`app.py` powered by Flask and Gunicorn) designed for easy central deployment. It removes the need to process Amazon CSVs locally.

### Key Web Features:
* 📥 **Interactive Drag-and-Drop Uploader**: Easily upload Amazon order history CSV exports directly from your web browser.
* ⚙️ **On-the-Fly Control Panel**: 
  * Toggles for **Dry Run** (simulates splits/matching output) and **Execute** (writes modifications directly to Actual Budget).
  * Toggle for **Force Recalculation** (overwrites existing tags).
  * Dynamic numerical input to adjust **Date Tolerance** (matching window days).
* 🖥️ **Real-time Observability Terminal**: An animated dark console that live-streams colorized execution logs, detailing product splits, parent associations, matching status, and errors.
* 🩺 **In-Cluster Diagnostics**: Accessible via the page footer, providing instant JSON feedback on the health of your `actual-http-api` connection and listing the synchronized budget accounts.
* 🐳 **Docker-Ready**: Easy to containerize using the included `Dockerfile` and secure behind path-based Traefik reverse proxies using HTTP Basic Authentication.

---

## Requirements

- Python 3.7 or higher
- `requests` library (for making HTTP calls to actual-http-api)
- Access to an Actual Budget instance with actual-http-api running
- CSV file of Amazon purchase history. See https://www.amazonforum.com/s/question/0D5at00000UHvv9CAD/how-to-download-transaction-reports-on-amazon-purchases-by-year for export directions.

## Installation

### Option 1: Direct Execution (No Installation)

The script can be run directly without installation:

```chmod +x actual-amazon-noter
./actual-amazon-noter --help
```

### Option 2: Install via pip

```bash
pip install -r requirements.txt
```


### Option 3: Install as a Package

```bash
pip install .
```

## Running actual-amazon-noter

### Running as a Web Companion (GUI)

You can launch the web interface locally by running:

```bash
pip install -r requirements.txt
python3 app.py
```

Then navigate to `http://localhost:8080` in your web browser. Make sure you have exported your `ACTUAL_HTTP_API_URL`, `ACTUAL_HTTP_API_KEY`, and `ACTUAL_SYNCID` environment variables first (see **Configuration** below).

### Running as a CLI Utility

Regardless of the installation method, make the file executable via ```chmod```, then run it:

```bash
chmod +x actual-amazon-noter
./actual-amazon-noter --help
```


## Configuration

The script requires three connection parameters to access the actual-http-api:

1. **API URL** - The URL of the actual-http-api server (e.g., http://localhost:5007)
2. **API Key** - The secret key used by actual-http-api
3. **Sync ID** - The synchronization ID for the budget instance

These can be provided in three ways:

### Option 1: Environment Variables

```bash
export ACTUAL_HTTP_API_URL=http://localhost:5007
export ACTUAL_HTTP_API_KEY=your-secret-key
export ACTUAL_SYNCID=your-sync-id
```

### Option 2: Command-Line Arguments

```bash
actual-amazon-noter \
    --actual-http-api http://localhost:5007 \
    --actual-http-api-key your-secret-key \
    --actual-syncid your-sync-id \
    Order_History.csv
```

### Option 3: Configuration Files

Create a file (e.g., `config.txt`) with multiple values:

```
ACTUAL_HTTP_API_URL=http://localhost:5007
ACTUAL_HTTP_API_KEY=your-secret-key
ACTUAL_SYNCID=your-sync-id
```

Then reference it:

```
actual-amazon-noter \
    --actual-http-api-file config.txt \
    --actual-http-key-file config.txt \
    --actual-syncid-file config.txt \
    Order_History.csv
```

Or use the bare string format (one value per file):

```
echo "http://localhost:5007" > url.txt
echo "your-secret-key" > key.txt
echo "your-sync-id" > syncid.txt
actual-amazon-noter \
    --actual-http-api-file /path/to/url.txt \
    --actual-http-api-key-file /path/to/key.txt \
    --actual-syncid-file /path/to/syncid.txt \
    Order_History.csv
```

## Usage

### Basic Usage (Dry-Run Mode)

By default, the script runs in dry-run mode and only displays what changes would be made:

```bash
actual-amazon-noter Order_History.csv
```

### Execute Changes

To actually update the records in Actual Budget, use the `--execute` flag:

```bash
actual-amazon-noter --execute Order_History.csv
```

### Date Tolerance

By default, transactions are matched if the Amazon date is within 3 days before the Actual Budget transaction. Change this with `--days`:

```bash
actual-amazon-noter --days 7 Order_History.csv
```

### Force Update

If a transaction already has Amazon tags but you want to replace them:

```bash
actual-amazon-noter --force Order_History.csv
```

## Amazon CSV File Formats

The only currently supported file format is **Order_History.csv** -- the standard order history (purchases) export

The tool is intended to support these Amazon data export files in the future:

- **Digital_Content_Orders.csv** - Digital content orders
- **Refund_Details.csv** - Refund details
- **Digital_Returns.csv** - Digital returns

## Command-Line Options

```
--dry-run [csv|json]    Show changes without updating (default: csv)
--execute               Actually update records in Actual Budget
--days X                Number of days tolerance for matching (default: 3)
--force                 Replace existing Amazon tags
--actual-http-api URL   API server URL
--actual-http-api-file /path/to/file    File containing API URL
--actual-http-api-key SecretKey        API key
--actual-http-api-key-file /path/to/file   File containing API key
--actual-syncid SyncID                  Budget SyncID
--actual-syncid-file /path/to/file      File containing SyncID
```

## Examples

### Example 1: Using environment variables

```bash
export ACTUAL_HTTP_API_URL=http://cubanalle:5007
export ACTUAL_HTTP_API_KEY=ef6678dee3fc4f44b7db53752c63621d
export ACTUAL_SYNCID=7cb4a210-b87f-4b38-8f07-1380e6c30b3c

actual-amazon-noter --execute Order_History.csv
```

### Example 2: Using a config file

```bash
# Create config file
echo "ACTUAL_HTTP_API_URL=http://cubanalle:5007" > config.txt
echo "ACTUAL_HTTP_API_KEY=ef6678dee3fc4f44b7db53752c63621d" >> config.txt
echo "ACTUAL_SYNCID=7cb4a210-b87f-4b38-8f07-1380e6c30b3c" >> config.txt

# Run the tool
actual-amazon-noter --actual-http-api-file config.txt \
                    --actual-http-key-file config.txt \
                    --actual-syncid-file config.txt \
                    --execute \
                    Order_History.csv
```

### Example 3: Preview changes before executing

## License

MIT.
