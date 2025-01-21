# Token Vesting App with FORDEFI

This repository contains a set of Python scripts that implement an automatic vesting schedule for digital assets custodied in Fordefi vaults. The design uses:
1. Google Cloud Secret Manager for securely storing API credentials
2. Firebase Firestore for managing vesting configurations
3. Fordefi API for executing on-chain transactions
4. Google Cloud VM for running the scripts

## Table of Contents

1. Overview
2. Prerequisites
3. Scripts
4. Setting Up
5. Configuration
6. Running the Vesting Manager
7. Troubleshooting & Tips
8. License

## Overview

The main script, `vesting_manager.py`, reads vesting schedules from Firestore and schedules them to occur at specific daily times. When it's time to vest:
- The script looks up the relevant asset, chain, vault ID, and transfer details
- A transaction is constructed and signed via an API Signer (using an ECDSA private key stored in Google Cloud Secret Manager)
- The transaction is broadcast to Fordefi's API, which executes the on-chain transfer from your Fordefi vault



## Prerequisites
1. Google Cloud Project:
   * Secret Manager enabled
   * Firestore in Native mode
   * Service account credentials for the GCP VM with permissions to access Secret Manager and Firestore
   * An Ubuntu VM
2. Python 3.8+ environment on your GCP VM (or local machine)
3. Installed Dependencies (listed below under Setting Up)
4. Fordefi account and associated vault(s). You will need:
   * The vault ID of your Fordefi vault
   * Your Fordefi user API token
   * An Fordefi API Signer set up.

## Scripts

This repository contains 5 Python scripts:

### 1. Vesting Manager

**File:** `vesting_manager.py`  
**Purpose:**
- Initializes Firebase (Firestore)
- Reads vesting configurations from Firestore
- Schedules each vesting to occur at the configured daily time
- Uses the appropriate transfer function (native or token) when the vesting time is reached

**Key Functions:**
- `load_vesting_configs()`
- `schedule_vesting_for_asset(cfg)`
- `execute_vest_for_asset(cfg)`
- `main()`

You will generally run this file to start the entire vesting scheduler.

### 2. API Signer

**File:** `api_signer.py`  
**Purpose:**
- Signs API requests with your FORDEFI API Signer.
- Fetches the AI Signer's ECDSA private key from GCP Secret Manager

**Key Function:**
- `sign(payload, project)`

## Setting Up

1. Clone or copy the repository onto your GCP VM.

2. Update your VM and install pip:
```bash
sudo apt-get update
sudo apt-get install python3-pip
```
3. Install required Python packages:
```bash
pip install google-cloud-secret-manager google-cloud-firestore firebase-admin ecdsa requests pytz schedule
```

4. Ensure your GCP VM has authentication set up:
- Typically done by assigning a Service Account to your VM with the roles:
  - Secret Manager Secret access:
  ```bash
  gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:MY_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
  ```
  - Cloud Datastore User (for Firestore)

## Configuration

### Firebase Firestore Structure

The `vesting_manager.py` script expects a Firestore collection named `vesting_configs`. Each document in `vesting_configs` corresponds to a vault ID. The document should look like:

## Configuration

### Firebase Firestore Structure

The `vesting_manager.py` script expects a Firestore collection named `vesting_configs`. Each document in `vesting_configs` corresponds to a vault ID. The document should look like:

```json
{
  "tokens": [
    {
      "asset": "BNB",
      "ecosystem": "evm",
      "type": "native",
      "chain": "bsc",
      "value": "0.000001",
      "note": "Daily BNB vesting",
      "cliff_days": 0,
      "vesting_time": "13:00",
      "destination": "0xYOUR_ADDRESS"
    },
    {
      "asset": "USDT",
      "ecosystem": "evm",
      "type": "erc20",
      "chain": "bsc",
      "value": "0.00001",
      "note": "Daily USDT vesting",
      "cliff_days": 0,
      "vesting_time": "19:00",
      "destination": "0xYOUR_ADDRESS"
    }
  ]
}
```


#### Fields explained:
- `vault_id` is the document ID in the collection
- `tokens` is an array of token-vesting objects
- `asset`: The token ticker (e.g., BNB, USDT)
- `ecosystem`: For EVM chains, use "evm"
- `type`: "native" for base chain assets (ETH, BNB), "erc20" for ERC-20 tokens
- `chain`: e.g., "bsc", "ethereum"
- `value`: The amount to vest, in normal "human-readable" units (e.g. 0.001 BNB)
- `note`: A description of the vesting purpose
- `cliff_days`: How many days to delay before the first vest
- `vesting_time`: 24-hour format string for daily vesting time in CET (the script automatically accounts for UTC conversions)
- `destination`: The receiving address for the vest

### Secrets in Google Cloud Secret Manager

Two secrets need to be created (names are placeholders — you can adjust them in your code if desired):

1. FORDEFI API SIgner's Private Key:
   - Secret Name: `PRIVATE_KEY_FILE`
   - Purpose: Used by api_signer.py to sign Fordefi transactions
   - Must be in PEM format with no password

2. Fordefi User API Token:
   - Secret Name: `USER_API_TOKEN`
   - Purpose: Bearer token for authorizing API calls to Fordefi

IMPORTANT: The code uses the secrets' latest version. Make sure you have a secret version named latest (which is automatically assigned to the newest secret version in GCP).

## Running the Vesting Manager

1. Make sure you have all 5 scripts organized as follow:
```
project_root/
├── vesting_manager.py
├── signer/
│   └── api_signer.py
├── secret_manager/
│   └── gcp_secret_manager.py
└── vesting_scripts/
    ├── transfer_token_gcp.py
    └── transfer_native_gcp.py
```

2. Start the vesting manager:
   ```bash
   python3 vesting_manager.py
   ```

3. Check the output:
   - The script will initialize Firebase
   - It will fetch each document from the `vesting_configs` collection
   - For each token in the Firestore doc, it will schedule a job to vest daily at the configured time
   - Logs will indicate the first vest date/time in UTC

4. Keep the script running:
   - It uses an internal `while True:` loop with `schedule.run_pending()`
   - However it's recommended to run this script as a background service (e.g., use systemd, supervisor, or Docker to keep it alive)

## Troubleshooting & Tips

1. Permissions:
   - Make sure your GCP VM service account has read access to the secrets in Secret Manager and read/write (as needed) for Firestore

2. Debugging:
   - The script prints error messages to the console if a vesting transfer fails
   - Check logs for any HTTP errors from the Fordefi API

3. Cliff Period:
   - If `cliff_days` is set to 0, vesting is scheduled starting today
   - If the daily vesting time is already passed for the current day, the script automatically pushes to tomorrow

4. EVM Chains & Tokens:
   - `transfer_token_gcp.py` includes minimal logic for contract addresses (e.g., USDT on BSC, USDT/PEPE on Ethereum, etc.)
   - If you need more tokens or chains, you must update these scripts accordingly

5. Time Zones:
   - The `vesting_time` is in CET
   - The script converts to UTC under the hood to ensure consistent scheduling

6. Extended Ecosystems:
   - Currently, the code includes references to EVM tokens
   - For non-EVM (e.g., Solana, Sui), you would need to expand the logic in `execute_vest_for_asset` and create new transfer scripts