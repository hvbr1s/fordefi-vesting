import schedule
import time
import pytz
from datetime import datetime, timedelta
from vesting_scripts.transfer_native_gcp import transfer_native_gcp
from vesting_scripts.transfer_token_gcp import transfer_token_gcp

def load_vesting_config():
    """
    Returns the config needed for the vesting schedule.
    
    `cliff_days`:  the number of days to wait before the first vest
    `vesting_time`: the time (in "HH:MM" UTC or CET) to vest each day
    """
    return {
        "cliff_days": 1,       # e.g. starts tomorrow
        "vesting_time": "06:00" # 24-hour format (CET in this example)
    }


def compute_first_vesting_date(cliff_days: int) -> datetime:
    """
    Returns the base date/time for the first vest in UTC.
    If the user sets cliff_days=1, we push the first vest out by 1 day.
    """
    now = datetime.now(datetime.UTC)
    return now + timedelta(days=cliff_days)


def execute_daily_vest():
    """
    This function is run once every day at 6 AM CET (after the cliff).
    In the final version, you might call out to your separate
    scripts (transfer_native_gcp.py / transfer_token_gcp.py) to do the actual transfers.
    """
    print("🔔 It's vesting time! Submitting daily transaction...")

    # Handle BNB transfer
    try:
        vest_bnb = transfer_native_gcp(
            chain="bsc",
            vault_id="652a2334-a673-4851-ad86-627781689592",
            destination="0xF659feEE62120Ce669A5C45Eb6616319D552dD93",
            value="0.0001",
            note="Daily vesting"
        )
        print("✅ BNB vesting completed successfully")
    except Exception as e:
        print(f"❌ Error during BNB vesting: {str(e)}")

    # Handle USDT transfer
    try:
        vest_usdt = transfer_token_gcp(
            chain="bsc",
            token_address="0xSomeTokenAddress",
            vault_id="652a2334-a673-4851-ad86-627781689592",
            destination="0xF659feEE62120Ce669A5C45Eb6616319D552dD93",
            amount="123.45",
            note="Daily vesting"
        )
        print("✅ USDT vesting completed successfully")
    except Exception as e:
        print(f"❌ Error during USDT vesting: {str(e)}")


def schedule_vesting():
    """
    1) Computes the next vesting date considering the cliff.
    2) Schedules a job daily at 6 AM CET starting from that date.
    """
    # Load config and parse
    config = load_vesting_config()
    cliff_days    = config["cliff_days"]
    vesting_time  = config["vesting_time"]  # e.g. "06:00" CET
    vest_hour, vest_minute = map(int, vesting_time.split(":"))
    
    # Compute the base date for the first vest in UTC
    first_vest_datetime_utc = compute_first_vesting_date(cliff_days)
    
    # Convert that date from UTC to CET
    cet = pytz.timezone("CET")
    localized_cliff_utc = pytz.utc.localize(first_vest_datetime_utc)
    cliff_in_cet = localized_cliff_utc.astimezone(cet)
    
    # Apply the desired vesting hour + minute in CET
    cliff_in_cet = cliff_in_cet.replace(
        hour=vest_hour,
        minute=vest_minute,
        second=0,
        microsecond=0
    )
    
    # If that time is in the past for the CET day, push it to the next day
    now_cet = datetime.now(tz=cet)
    if cliff_in_cet <= now_cet:
        cliff_in_cet += timedelta(days=1)
    
    # Convert this "6:00 CET after cliff" back to UTC for scheduling
    first_run_utc = cliff_in_cet.astimezone(pytz.utc)
    print(f"⏰ First vest scheduled for: {first_run_utc} UTC")
    
    # Use a one-shot "launcher" job to wait until first_run_utc, then schedule daily
    def job_launcher():
        now_utc = datetime.now(datetime.UTC)
        if now_utc >= first_run_utc:
            # The time has arrived or passed — do the vest now
            execute_daily_vest()
            # Then schedule it to repeat every 24 hours
            schedule.every(24).hours.do(execute_daily_vest)
            return schedule.CancelJob  # we only want to do this check once

    # We'll check every minute whether it's time to launch the first vest
    schedule.every(1).minutes.do(job_launcher)


if __name__ == "__main__":
    schedule_vesting()
    # Keep the script alive checking for scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(10)