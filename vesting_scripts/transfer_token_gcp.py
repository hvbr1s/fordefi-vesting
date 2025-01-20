import requests
import base64
import json
import datetime
from decimal import Decimal
from signer.api_signer import sign
from secret_manager.gcp_secret_manager import access_secret


### FUNCTIONS
def broadcast_tx(path, access_token, signature, timestamp, request_body):

    try:
        resp_tx = requests.post(
            f"https://api.fordefi.com{path}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-signature": base64.b64encode(signature),
                "x-timestamp": timestamp.encode(),
            },
            data=request_body,
        )
        resp_tx.raise_for_status()
        return resp_tx

    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error occurred: {str(e)}"
        if resp_tx.text:
            try:
                error_detail = resp_tx.json()
                error_message += f"\nError details: {error_detail}"
            except json.JSONDecodeError:
                error_message += f"\nRaw response: {resp_tx.text}"
        raise RuntimeError(error_message)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error occurred: {str(e)}")


def evm_tx_tokens(evm_chain, vault_id, destination, custom_note, value, token):

    sanitized_token_name = token.lower().strip()

    value_eighteen_decimal_tokens = str(int(Decimal(value) * Decimal('1000000000000000000'))) # 18 decimals
    value_six_decimal_tokens =  str(int(Decimal(value) * Decimal('1000000')))  # 6 decimals

    if evm_chain == "bsc":
        if sanitized_token_name == "usdt":
            contract_address = "0x55d398326f99059fF775485246999027B3197955"
            value = value_eighteen_decimal_tokens
        else:
            raise ValueError(f"Token '{token}' is not supported for chain '{evm_chain}'") 
    elif evm_chain == "ethereum":
        if sanitized_token_name == "usdt":
            contract_address = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
            value = value_six_decimal_tokens 
        elif sanitized_token_name == "pepe":
            contract_address = "0x6982508145454Ce325dDbE47a25d4ec3d2311933"
            value = value_eighteen_decimal_tokens
        elif sanitized_token_name == "basedai":
            contract_address = "0x44971ABF0251958492FeE97dA3e5C5adA88B9185"
            value = value_eighteen_decimal_tokens
        else:
            raise ValueError(f"Token '{token}' is not supported for chain '{evm_chain}'") 
    else:
        raise ValueError(f"Token '{token}' is not supported for chain '{evm_chain}'")

    request_json =  {
    "signer_type": "api_signer",
    "type": "evm_transaction",
    "details": {
        "type": "evm_transfer",
        "gas": {
          "type": "priority",
          "priority_level": "medium"
        },
        "to": destination,
        "value": {
           "type": "value",
           "value": value
        },
        "asset_identifier": {
             "type": "evm",
             "details": {
                 "type": "erc20",
                 "token": {
                     "chain": f"evm_{evm_chain}_mainnet",
                     "hex_repr": contract_address
                 }
             }
        }
    },
    "note": custom_note,
    "vault_id": vault_id
}

    return request_json

### Core logic
def transfer_token_gcp(chain, token_ticker, vault_id, destination, amount, note):
    """
    Execute an ERC20 token transfer using Fordefi API
    
    Args:
        chain (str): Chain identifier (e.g., "bsc", "eth")
        token_address (str): Contract address of the token
        vault_id (str): Fordefi vault ID
        destination (str): Destination wallet address
        amount (str): Amount to transfer in token units (e.g., "123.45")
        note (str): Transaction note
    
    Returns:
        dict: Response from the Fordefi API
    """
    # Set config
    GCP_PROJECT_ID = 'inspired-brand-447513-i8'
    FORDEFI_API_USER_TOKEN = 'USER_API_TOKEN'
    USER_API_TOKEN = access_secret(GCP_PROJECT_ID, FORDEFI_API_USER_TOKEN, 'latest')
    path = "/api/v1/transactions"

    # Building transaction
    request_json = evm_tx_tokens(
        evm_chain=chain,
        vault_id=vault_id,
        destination=destination,
        custom_note=note,
        value=amount,
        token=token_ticker
    )
    request_body = json.dumps(request_json)
    timestamp = datetime.datetime.now().strftime("%s")
    payload = f"{path}|{timestamp}|{request_body}"

    # Sign transaction with API Signer
    signature = sign(payload=payload, project=GCP_PROJECT_ID)

    # Broadcast tx
    resp_tx = broadcast_tx(path, USER_API_TOKEN, signature, timestamp, request_body)
    return resp_tx.json()