import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


STEP_BY_INTERVAL = {
    "1s": timedelta(seconds=1),
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
}


def create_session_with_retries(max_retries: int = 3, backoff_factor: float = 0.5):
    """Create a requests session with automatic retry logic for connection failures."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP statuses
        allowed_methods=["GET"],  # Only retry GET requests
        raise_on_status=False,  # Don't raise immediately, let us handle it
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def iter_bucket_starts(start: datetime, end: datetime, step: timedelta):
    current = start
    while current <= end:
        yield current
        current += step


def fetch_candle(api_key: str, market: str, interval: str, bucket_start: datetime, session: requests.Session = None):
    """Fetch a single candle with automatic retry logic."""
    if session is None:
        session = create_session_with_retries()
    
    max_manual_retries = 2  # Reduced from 3
    for attempt in range(max_manual_retries):
        try:
            response = session.get(
                f"https://api-hyperliquid-index.n.dwellir.com/{api_key}/v1/candles",
                params={
                    "market": market,
                    "interval": interval,
                    "time": format_utc(bucket_start),
                },
                timeout=15,  # Reduced from 30
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt < max_manual_retries - 1:
                wait_time = min(2 ** attempt, 5)  # Cap at 5 seconds
                print(f"Request error: {e}, manual retry in {wait_time}s... (attempt {attempt + 1}/{max_manual_retries})", file=sys.stderr)
                time.sleep(wait_time)
            else:
                print(f"Giving up on {format_utc(bucket_start)} after {max_manual_retries} attempts", file=sys.stderr)
                return None  # Return None instead of raising to skip this timestamp

    return None


def export_csv(api_key: str, market: str, interval: str, start: str, end: str, output_path: str):
    if interval not in STEP_BY_INTERVAL:
        raise ValueError(f"unsupported interval: {interval}")

    start_dt = parse_utc(start)
    end_dt = parse_utc(end)
    step = STEP_BY_INTERVAL[interval]
    
    # Check if we're resuming from an existing file
    resume_mode = False
    if os.path.exists(output_path):
        # Read the last timestamp from the existing file
        try:
            with open(output_path, "r", newline="") as handle:
                reader = csv.DictReader(handle)
                last_row = None
                for last_row in reader:
                    pass
                
                if last_row and "t" in last_row:
                    # "t" is the bucket time in milliseconds
                    last_ts_ms = int(last_row["t"])
                    last_dt = datetime.fromtimestamp(last_ts_ms / 1000.0, tz=timezone.utc)
                    # Resume from the next interval
                    start_dt = last_dt + step
                    resume_mode = True
                    print(f"Resuming from {format_utc(start_dt)}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not read existing file, starting fresh: {e}", file=sys.stderr)
    
    # Create a session once and reuse it for all requests
    session = create_session_with_retries(max_retries=3, backoff_factor=0.5)

    # Open in append mode if resuming, write mode if starting fresh
    file_mode = "a" if resume_mode else "w"
    with open(output_path, file_mode, newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "s",
                "i",
                "t",
                "T",
                "o",
                "h",
                "l",
                "c",
                "v",
                "q",
                "n",
                "x",
            ],
        )
        # Only write header if starting fresh
        if not resume_mode:
            writer.writeheader()

        candle_count = 0
        consecutive_skips = 0
        max_consecutive_skips = 100  # Stop if we skip 100 timestamps in a row
        
        for bucket_start in iter_bucket_starts(start_dt, end_dt, step):
            candle = fetch_candle(api_key, market, interval, bucket_start, session=session)
            if candle is None:
                consecutive_skips += 1
                if consecutive_skips >= max_consecutive_skips:
                    print(f"Stopped after {consecutive_skips} consecutive skips - no more data available from {format_utc(bucket_start)}", file=sys.stderr)
                    break
                continue
            
            consecutive_skips = 0  # Reset skip counter
            writer.writerow(candle)
            candle_count += 1
            
            # Print progress every 100 candles
            if candle_count % 100 == 0:
                print(f"Downloaded {candle_count} total candles, last: {format_utc(bucket_start)}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 7:
        raise SystemExit(
            "usage: python export_ohlcv_csv.py <API_KEY> <MARKET> <INTERVAL> <START> <END> <OUT_CSV>"
        )

    _, api_key, market, interval, start, end, output_path = sys.argv
    export_csv(api_key, market, interval, start, end, output_path)