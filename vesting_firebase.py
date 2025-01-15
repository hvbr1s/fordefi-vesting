import schedule
import time
import pytz
from datetime import datetime, timedelta
from vesting_scripts.transfer_native_gcp import transfer_native_gcp
from vesting_scripts.transfer_token_gcp import transfer_token_gcp
from firebase_admin import credentials, firestore
import firebase_admin


def load_vesting_configs():
    """
    Loads vesting configs from Firestore's 'vault_configs' collection.
    Each document should have fields like:
      - asset, type, chain, vault_id, destination, note, cliff_days, vesting_time
      - Either 'value' (for native) or 'amount' (for ERC20).
    Returns a list of config dictionaries.
    """
    # Initialize Firebase Admin if not already
    if not firebase_admin._apps:
        cred = credentials.Certificate("path/to/serviceAccountKey.json")
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    
    configs = []
    docs = db.collection("vault_configs").stream()
    
    for doc in docs:
        data = doc.to_dict()

        asset = data.get("asset")
        type = data.get("type")
        chain = data.get("chain")
        vault_id = data.get("vault_id")
        destination = data.get("destination")
        note = data.get("note", f"{asset} daily vesting")
        cliff_days = data.get("cliff_days", 0)
        vesting_time = data.get("vesting_time", "00:00")
        
        cfg = {
            "asset": asset,
            "type": type,
            "chain": chain,
            "vault_id": vault_id,
            "destination": destination,
            "note": note,
            "cliff_days": cliff_days,
            "vesting_time": vesting_time
        }
        
        if type == "native":
            cfg["value"] = data.get("value", "0")
        else:
            cfg["amount"] = data.get("amount", "0")
        
        configs.append(cfg)
    
    return configs


def compute_first_vesting_date(cliff_days: int) -> datetime:
    now = datetime.now(pytz.UTC)
    return now + timedelta(days=cliff_days)


def execute_vest_for_asset(cfg: dict):
    print(f"\n🔔 It's vesting time for {cfg['asset']} (Vault ID: {cfg['vault_id']})!")
    try:
        if cfg["type"] == "native":
            transfer_native_gcp(
                chain=cfg["chain"],
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                value=cfg["value"],
                note=cfg["note"]
            )
        else:
            transfer_token_gcp(
                chain=cfg["chain"],
                token_ticker=cfg["asset"].lower(),
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                value=cfg["value"],
                note=cfg["note"]
            )

        print(f"✅ {cfg['asset']} vesting completed successfully")
    except Exception as e:
        print(f"❌ Error during {cfg['asset']} vesting: {str(e)}")


def schedule_vesting_for_asset(cfg: dict):
    cliff_days = cfg["cliff_days"]
    vesting_time = cfg["vesting_time"]
    vest_hour, vest_minute = map(int, vesting_time.split(":"))

    first_vest_datetime_utc = compute_first_vesting_date(cliff_days)

    cet = pytz.timezone("CET")
    cliff_in_cet = first_vest_datetime_utc.astimezone(cet)
    cliff_in_cet = cliff_in_cet.replace(
        hour=vest_hour, minute=vest_minute, second=0, microsecond=0
    )

    now_cet = datetime.now(tz=cet)
    if cliff_in_cet <= now_cet:
        cliff_in_cet += timedelta(days=1)

    first_run_utc = cliff_in_cet.astimezone(pytz.UTC)
    print(f"⏰ {cfg['asset']} (Vault ID: {cfg['vault_id']}) first vest scheduled for: {first_run_utc} UTC")

    def job_launcher():
        now_utc = datetime.now(pytz.UTC)
        if now_utc >= first_run_utc:
            execute_vest_for_asset(cfg)
            schedule.every(24).hours.do(execute_vest_for_asset, cfg)
            return schedule.CancelJob

    schedule.every(1).minutes.do(job_launcher)


def main():
    configs = load_vesting_configs()
    for cfg in configs:
        schedule_vesting_for_asset(cfg)

    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()