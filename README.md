# actual-ecommerce-noter

A companion utility and web companion for [Actual Budget](https://actualbudget.org) that enriches transaction records with purchase details from Amazon and PayPal CSV exports.

Rather than importing transactions directly into a new ledger (which introduces duplicate overhead and complex currency conversion math), this tool enriches existing bank/card transactions with line-item detail and creates structural split transactions natively using Actual Budget's REST API.

---

## Key Features

- **Structural Split Transactions**: Converts multi-item orders into parent-child split transactions in your Actual Budget UI, pre-populated with exact item prices and individual notes.
- **PayPal UK Correlation**: Filters for `Completed` status, ignores internal card deposit buffers, and automatically matches EUR/USD foreign currency purchases to their GBP equivalents by correlating adjacent General Currency Conversion entries.
- **Smart Explicit Format Selection**: Provides explicit dropdown selection in the GUI and a `--format amazon|paypal|auto` flag in the CLI to avoid header schema ambiguities.
- **Integrated Web Interface**: Features an interactive dashboard with a drag-and-drop CSV uploader, execution controls, dry-run simulation, real-time colorized logs, and raw connection diagnostics.
- **Multi-Currency Support**: Dynamically extracts currency details from the source CSV to ensure dry-run previews and split notes are accurately localized.

---

## Design Decisions & Matching Logic

### Why Noting instead of Ledger Imports?
Ledger imports of e-commerce statements often result in transaction duplication and bypass native bank account feeds. By choosing **Noting**, the tool matches and enriches already imported bank or credit card transactions, preserving the correct, cleared exchange rates and bank statement records.

### Why Standard PayPal CSV over QuickBooks IIF?
While the QuickBooks IIF format offers consistent item descriptions, it strips PayPal's unique Transaction and Receipt IDs. Without these hashes, matching is vulnerable to duplicate annotations when multiple transactions of identical amounts occur on the same day. Using the **Standard CSV** allows the tool to generate precise tags anchored by the `#PayPal-Transaction-ID <ID>` hash, ensuring duplicate protection and safety.

### Dynamic Date Tolerance
E-commerce bank clearing times vary by payment mechanism:
- **Amazon (Default: 3 Days)**: Direct credit/debit card transactions typically clear on standard bank statements within 3 days.
- **PayPal (Default: 7 Days)**: Bank transactions for PayPal settlements take up to **a week (7 days)** because PayPal operates as a pass-through wallet (funding transfers, eChecks, and bank clearing delays).

The tool automatically shifts its matching date tolerance to 7 days when the PayPal format is selected or detected.

### Comparative Amount Tolerance & Payee Verification
Different e-commerce platforms necessitate distinct matching strictness:
- **Amazon (Default: £1.00 / 100 cents)**: Amazon orders are often split dynamically into multiple sub-shipments (which clear the bank as separate, minor charge adjustments) or include additional local taxes/shipping charges. A higher amount tolerance of up to £1.00 allows matching these split charges with the parent order.
- **PayPal (Default: £0.00 / 0 cents)**: PayPal operates on exact passthrough bank settlement amounts. Because bank statement debits align exactly with the PayPal ledger transaction, any amount variance represents a distinct transaction. The tool enforces a strict **£0.00 amount tolerance** for PayPal matches, completely eliminating false-positive subscription mappings.
- **Payee String Validation**: For PayPal transactions, the tool extracts alphanumeric keywords from the budget transaction payee and correlates them against the PayPal CSV's merchant Name (ignoring generic words like *PayPal*, *payment*, *ltd*). Specific merchant codes (e.g. `ROBLOX` vs `LEBARA`) are strictly segregated, preventing cross-matching (swapping) of near-identical small amounts on close dates.

---

## Configuration

The utility requires connection parameters for your `actual-http-api` instance:

1. **API URL** (`ACTUAL_HTTP_API_URL`): The URL of your actual-http-api server (e.g., `http://localhost:5007`).
2. **API Key** (`ACTUAL_HTTP_API_KEY`): The secret key used by actual-http-api.
3. **Sync ID** (`ACTUAL_SYNCID`): The synchronization ID for your specific budget.

### Providing Configuration

These parameters can be provided via environment variables, CLI flags, or file-based configuration.

#### Option 1: Environment Variables
```bash
export ACTUAL_HTTP_API_URL=http://localhost:5007
export ACTUAL_HTTP_API_KEY=your-secret-key
export ACTUAL_SYNCID=your-sync-id
```

#### Option 2: Command-Line Arguments
```bash
actual-ecommerce-noter \
    --actual-http-api http://localhost:5007 \
    --actual-http-api-key your-secret-key \
    --actual-syncid your-sync-id \
    Order_History.csv
```

#### Option 3: Configuration Files (e.g. `config.txt`)
```ini
ACTUAL_HTTP_API_URL=http://localhost:5007
ACTUAL_HTTP_API_KEY=your-secret-key
ACTUAL_SYNCID=your-sync-id
```
```bash
actual-ecommerce-noter --actual-http-api-file config.txt Order_History.csv
```

---

## CLI Usage

### Basic Usage (Dry-Run Mode)
Runs a dry-run and prints proposed budget matches to stdout:
```bash
chmod +x actual-ecommerce-noter
./actual-ecommerce-noter Order_History.csv
```

### Execute Changes
Applies the updates directly to your Actual Budget instance:
```bash
./actual-ecommerce-noter --execute Order_History.csv
```

### Custom Date Tolerance & Format Override
```bash
./actual-ecommerce-noter --days 10 --format paypal Paypal_Download.csv
```

### Custom Tags
Append custom tags (e.g., `#invoice` or `#follow-up`) to matched transactions:
```bash
./actual-ecommerce-noter -t "invoice" -t "needs verification" Order_History.csv
```

### CLI Options Reference
```
--dry-run [csv|json]    Show changes without updating (default: csv)
--execute               Actually update records in Actual Budget
--days X                Number of days tolerance for matching
--amount-tolerance X    Max amount tolerance in currency units (e.g. 1.00 or 0.00)
--format amazon|paypal  Explicitly set the CSV schema format
--force                 Replace existing e-commerce tags
--actual-http-api URL   API server URL
--actual-http-api-file  File containing API URL
--actual-http-api-key   API key
--actual-syncid SyncID  Budget Sync ID
-t, --tag TAG           Custom tag to append (can be specified multiple times)
```

---

## Web Interface

To host the web dashboard locally:
```bash
pip install -r requirements.txt
python3 app.py
```
Access the interface at `http://localhost:8080`.

---

## Kubernetes Deployment Examples

To deploy the web companion persistently in a Kubernetes (or K3s) cluster, follow these steps.

### 1. Build and Import the Image
Because this companion uses a customized local build, you must build the Docker image and make it available to your Kubernetes nodes before deploying:

```bash
# Build the image locally
docker build -t actual-ecommerce-noter:1.0.1 .

# Save and import the image into containerd on your nodes:
docker save actual-ecommerce-noter:1.0.1 -o actual-ecommerce-noter.tar
sudo k3s ctr images import actual-ecommerce-noter.tar
```

### 2. Deployment Manifests

#### Traefik Routing & Middleware
```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: actual-ecommerce-noter-strip
  namespace: finance
spec:
  stripPrefix:
    prefixes:
      - /actual-ecommerce-noter

---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: actual-ingress
  namespace: finance
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`actual.example.com`) && PathPrefix(`/actual-ecommerce-noter`)
      kind: Rule
      middlewares:
        - name: actual-sync-auth              # HTTP Basic Auth middleware reference
          namespace: finance
        - name: actual-ecommerce-noter-strip
          namespace: finance
      services:
        - name: actual-ecommerce-noter
          port: 8080
          namespace: finance
```

#### Deployment & Service
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: actual-ecommerce-noter
  namespace: finance
spec:
  replicas: 1
  selector:
    matchLabels:
      app: actual-ecommerce-noter
  template:
    metadata:
      labels:
        app: actual-ecommerce-noter
    spec:
      containers:
      - name: uploader
        image: actual-ecommerce-noter:1.0.1
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
        env:
        - name: ACTUAL_HTTP_API_URL
          value: "http://actual-http-api:5007"
        - name: ACTUAL_HTTP_API_KEY
          valueFrom:
            secretKeyRef:
              name: finance-secrets
              key: ACTUAL_HTTP_API_KEY
        - name: ACTUAL_SYNCID
          value: "YOUR-BUDGET-SYNC-ID"

---
apiVersion: v1
kind: Service
metadata:
  name: actual-ecommerce-noter
  namespace: finance
spec:
  selector:
    app: actual-ecommerce-noter
  ports:
    - port: 8080
      targetPort: 8080
```

---

## License

MIT.
