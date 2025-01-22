import schedule
import time
import pytz
import firebase_admin
from datetime import datetime, timedelta
from vesting_scripts.transfer_native_gcp import transfer_native_gcp
from vesting_scripts.transfer_token_gcp import transfer_token_gcp
from firebase_admin import firestore

# -------------------------------------------------
# UTILITY
# This script lets you implement a vesting schedule for assets custodied in Fordefi Vaults 
# Each asset config is stored in Firebase for easier management
# -------------------------------------------------

def load_vesting_configs():
    """
    Fetches vesting configurations from a Firestore collection named 'vesting_configs'.
    Returns a list of config dictionaries.
    """
    db = firestore.client()
    configs = []

    docs = db.collection("vesting_configs").stream()
    for doc in docs:
        doc_data = doc.to_dict()
        vault_id = doc.id
        tokens = doc_data.get("tokens", [])
        for token_info in tokens:
            cfg = {
                "vault_id":     vault_id,
                "asset":        token_info["asset"],
                "ecosystem":    token_info["ecosystem"],
                "type":         token_info["type"],
                "chain":        token_info["chain"],
                "destination":  token_info["destination"],
                "value":        token_info["value"],
                "note":         token_info["note"],
                "cliff_days":   token_info["cliff_days"],
                "vesting_time": token_info["vesting_time"]
            }
            configs.append(cfg)

    return configs


def compute_first_vesting_date(cliff_days: int) -> datetime:
    """
    Returns a base date/time in UTC for the first vest.
    If cliff_days=1, the first vest is pushed out by 1 day from now.
    """
    now = datetime.now(pytz.UTC)
    return now + timedelta(days=cliff_days)


def execute_vest_for_asset(cfg: dict):
    """
    Execute a single vest for the given asset/config.
    """
    print(f"\n🔔 It's vesting time for {cfg['asset']} (Vault ID: {cfg['vault_id']})!")
    try:
        if cfg["type"] == "native" and cfg["ecosystem"] == "evm" and cfg["value"] != "0":
            # Send native EVM token (e.g., BNB, ETH)
            transfer_native_gcp(
                chain=cfg["chain"],
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                value=cfg["value"],
                note=cfg["note"]
            )
        elif cfg["type"] == "erc20" and cfg["ecosystem"] == "evm" and cfg["value"] != "0":
            # Send ERC20 token (USDT, USDC, etc.)
            transfer_token_gcp(
                chain=cfg["chain"],
                token_ticker=cfg["asset"].lower(),
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                amount=cfg["value"],
                note=cfg["note"]
            )
        elif cfg["value"] == "0":
            # If the vesting amount is zero, print so
            print(f'❌ Vesting amount for {cfg["asset"]} in Firebase is 0!')

        else:
            raise ValueError(f"Unsupported configuration: type={cfg['type']}, ecosystem={cfg['ecosystem']}")

        print(f"✅ {cfg['asset']} vesting completed successfully.")
    except Exception as e:
        print(f"❌ Error during {cfg['asset']} vesting: {str(e)}")


def schedule_vesting_for_asset(cfg: dict, tag: str = "vesting"):
    """
    Computes the date/time for the first vest in CET, applies cliff_days + vesting_time,
    then sets up a 'launcher' job that schedules a daily vest for this asset.
    The extra 'tag' param lets us group these jobs so we can clear them later if needed.
    """
    cliff_days = cfg["cliff_days"]
    vesting_time = cfg["vesting_time"] 
    vest_hour, vest_minute = map(int, vesting_time.split(":"))

    # Compute the base vest date in UTC
    first_vest_datetime_utc = compute_first_vesting_date(cliff_days)

    # Convert that to CET and override hour/minute
    cet = pytz.timezone("CET")
    cliff_in_cet = first_vest_datetime_utc.astimezone(cet)
    cliff_in_cet = cliff_in_cet.replace(
        hour=vest_hour,
        minute=vest_minute,
        second=0,
        microsecond=0
    )

    # If that time is already in the past for today, push to the next day
    now_cet = datetime.now(tz=cet)
    if cliff_in_cet <= now_cet:
        cliff_in_cet += timedelta(days=1)

    # Convert back to UTC for scheduling
    first_run_utc = cliff_in_cet.astimezone(pytz.UTC)
    print(f"⏰ {cfg['asset']} (Vault ID: {cfg['vault_id']}) first vest scheduled for: {first_run_utc} UTC")

    def job_launcher():
        now_utc = datetime.now(pytz.UTC)
        if now_utc >= first_run_utc:
            # Vest now
            execute_vest_for_asset(cfg)
            # Then schedule to repeat every 24 hours
            schedule.every(24).hours.do(execute_vest_for_asset, cfg).tag(tag)
            return schedule.CancelJob

    # Check every minute if it's time to run; group them with .tag(tag)
    schedule.every(1).minutes.do(job_launcher).tag(tag)


def refresh_vesting_schedules():
    """
    Clears out existing vesting jobs, reloads configs, and re-schedules them.
    We call this at midnight every day so new config entries are picked up.
    """
    print("\n--- Refreshing vesting schedules from Firestore ---")
    # 1) Clear old vesting jobs (tag='vesting')
    schedule.clear('vesting')

    # 2) Load updated configs
    configs = load_vesting_configs()
    print(f"Loaded {len(configs)} vesting configs.")

    # 3) Re-schedule tasks for each config
    for cfg in configs:
        schedule_vesting_for_asset(cfg, tag="vesting")


def main():
    # 1) Init Firebase
    firebase_admin.initialize_app()
    print("Firebase initialized successfully!")

    # 2) Immediately do an initial refresh (so we have tasks right away)
    refresh_vesting_schedules()

    # 3) Schedule a daily refresh at 4pm CET
    schedule.every().day.at("16:00", "CET").do(refresh_vesting_schedules)

    # 4) Keep the script alive
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()