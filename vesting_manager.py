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
# This script lets you implement a vesting schedule for assets 
# custodied in Fordefi Vaults. Each asset config is stored in Firebase 
# for easier management.
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
                token_ticker=cfg["asset"],
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                amount=cfg["value"],
                note=cfg["note"]
            )
        elif cfg["value"] == "0":
            # If the vesting amount is zero, just inform
            print(f'❌ Vesting amount for {cfg["asset"]} in Firebase is 0!')
        else:
            raise ValueError(f"Unsupported configuration: type={cfg['type']}, ecosystem={cfg['ecosystem']}")

        print(f"✅ {cfg['asset']} vesting completed successfully.")
    except Exception as e:
        print(f"❌ Error during {cfg['asset']} vesting: {str(e)}")


def schedule_vesting_for_asset(cfg: dict, tag: str = "vesting"):
    """
    We take the vesting time (HH:MM) and cliff_days from cfg, and do the following:

    1) Compute the local day/time for the very first vest (including cliff_days).
    2) If that time is already in the past 'today', push it to tomorrow.
    3) Schedule that job to run daily at vest_hour:vest_minute (local system time).

    NOTE: 'schedule' library by default runs on the system's local time.
    If your server runs in UTC, you may want to:
      - either do everything in UTC,
      - or specify `pytz.timezone("Europe/Berlin")` if you want it to match CET always.
    """
    vest_hour, vest_minute = map(int, cfg["vesting_time"].split(":"))

    # We'll still do a 'cliff_days' offset from now (in UTC).
    now_utc = datetime.now(pytz.UTC)
    first_vest_date_utc = now_utc + timedelta(days=cfg["cliff_days"])

    # Convert from UTC to your local server time zone (or pick a specific zone).
    local_tz = pytz.timezone("CET")  # Or "CET", or "Europe/Paris", etc.
    first_vest_local = first_vest_date_utc.astimezone(local_tz)

    # Now apply the vest_hour:vest_minute
    first_vest_local = first_vest_local.replace(
        hour=vest_hour,
        minute=vest_minute,
        second=0,
        microsecond=0
    )

    # If we've passed that local time for the day, push to tomorrow
    now_local = datetime.now(local_tz)
    if first_vest_local <= now_local:
        first_vest_local += timedelta(days=1)

    # Format the HH:MM in local time for schedule.every().day.at("HH:MM")
    at_string = first_vest_local.strftime("%H:%M")

    # Define a small function that calls the vest
    def daily_vest_job():
        execute_vest_for_asset(cfg)

    # Schedule the job every day at the local time "at_string"
    schedule.every().day.at(at_string).do(daily_vest_job).tag(tag)

    print(f"⏰ {cfg['asset']} (Vault ID: {cfg['vault_id']}) first daily vest scheduled for {first_vest_local} local time.")


def refresh_vesting_schedules():
    """
    Clears out existing vesting jobs, reloads configs, and re-schedules them.
    We call this daily so that any new config entries are picked up.
    """
    print("\n--- Refreshing vesting schedules from Firestore ---")
    schedule.clear('vesting')

    configs = load_vesting_configs()
    print(f"Loaded {len(configs)} vesting configs.")

    for cfg in configs:
        schedule_vesting_for_asset(cfg, tag="vesting")


def main():
    # 1) Initialize Firebase
    firebase_admin.initialize_app()
    print("Firebase initialized successfully!")

    # 2) Initial refresh so we have tasks immediately
    refresh_vesting_schedules()

    # 3) Schedule a daily refresh at 4pm CET (using schedule’s time syntax)
    #    This refresh uses the local system time zone.
    schedule.every().day.at("16:00", "CET").do(refresh_vesting_schedules)

    # 4) Keep the script alive
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()