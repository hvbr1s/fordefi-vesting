import schedule
import time
import pytz
from datetime import datetime, timedelta
from vesting_scripts.transfer_native_gcp import transfer_native_gcp
from vesting_scripts.transfer_token_gcp import transfer_token_gcp


def load_vesting_configs():
    """
    Returns a list of per-asset configs, each containing:
      - vault_id
      - asset: the asset ticker
      - ecosystem: evm, solana, etc
      - type: 'native' or 'erc20'
      - chain: e.g. 'bsc' or 'ethereum'
      - destination: The address where tokens are sent
      - note: An optional note
      - cliff_days: How many days until the first vest
      - vesting_time: "HH:MM" (24:00 format)
      - value: string representation of amount to send
    """

    vault_configs = {
        "652a2334-a673-4851-ad86-627781689592": [ # Vault ID
            {
                "asset": "BNB",
                "ecosystem": "evm",
                "type": "native",
                "chain": "bsc",
                "value": "0.000001",
                "note": "Daily BNB vesting",
                "cliff_days": 0,
                "vesting_time": "18:00",
                "destination": "0xF659feEE62120Ce669A5C45Eb6616319D552dD93"
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
                "destination": "0xF659feEE62120Ce669A5C45Eb6616319D552dD93"
            }
        ],
        # Add more vault IDs here if needed
    }

    configs = []
    # Convert these dict entries into a list of full config objects
    for vault_id, token_list in vault_configs.items():
        for data in token_list:
            cfg = {
                "vault_id": vault_id,
                "asset": data["asset"],
                "ecosystem": data["ecosystem"],
                "type": data["type"],
                "chain": data["chain"],
                "destination": data["destination"],
                "value": data["value"],
                "note": data["note"],
                "cliff_days": data["cliff_days"],
                "vesting_time": data["vesting_time"]
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
    If 'type' is 'native', use transfer_native_gcp.
    If 'type' is 'erc20', use transfer_token_gcp.
    """
    print(f"\n🔔 It's vesting time for {cfg['asset']} (Vault ID: {cfg['vault_id']})!")
    try:
        if cfg["type"] == "native" and cfg["ecosystem"] == "evm":
            # Send native token (e.g., BNB or ETH)
            transfer_native_gcp(
                chain=cfg["chain"],
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                value=cfg["value"],
                note=cfg["note"]
            )
        elif cfg["type"] == "erc20" and cfg["ecosystem"] == "evm":
            # Send ERC20 token (e.g. USDT)
            transfer_token_gcp(
                chain=cfg["chain"],
                token_ticker=cfg["asset"].lower(),
                vault_id=cfg["vault_id"],
                destination=cfg["destination"],
                value=cfg["value"],
                note=cfg["note"]
            )
        else:
            # Fallback or handle other ecosystems if needed
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
    """
    Computes the date/time for the first vest in CET, applies cliff_days + vesting_time,
    then sets up a 'launcher' job that schedules a daily vest for this asset.
    """
    cliff_days = cfg["cliff_days"]
    vesting_time = cfg["vesting_time"]  # e.g. "06:00"
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
        # Check if we've reached/passed the first vest time in UTC
        now_utc = datetime.now(pytz.UTC)
        if now_utc >= first_run_utc:
            # Do the vest now
            execute_vest_for_asset(cfg)
            # Then schedule to repeat every 24 hours
            schedule.every(24).hours.do(execute_vest_for_asset, cfg)
            return schedule.CancelJob  # so this launcher job doesn't keep repeating

    # Check every minute if it's time to launch this asset's vest
    schedule.every(1).minutes.do(job_launcher)


def main():
    # Load multiple per-asset configs
    configs = load_vesting_configs()

    # For each asset, schedule its vest
    for cfg in configs:
        schedule_vesting_for_asset(cfg)

    # Keep the script alive
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()