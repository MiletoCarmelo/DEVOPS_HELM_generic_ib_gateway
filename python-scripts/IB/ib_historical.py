"""
Interactive Brokers (IB) Historical Data Client

This module provides a professional interface for retrieving historical market data
from Interactive Brokers using their API. It supports multiple timeframes,
customizable data formats, and includes comprehensive error handling.

Features:
    - Environment-based configuration
    - Multiple verbosity levels
    - Detailed error handling
    - Automatic data formatting
    - CSV export capabilities
    - Thread-safe implementation

Configuration:
    Required environment variables (in .env file):
    - IB_HOST: IB Gateway host (default: '127.0.0.1')
    - IB_PORT: IB Gateway port (default: 4001)
    - IB_CLIENT_ID: API client ID (default: 123)

Usage:
    Basic usage:
        >>> from ib_data_client import get_ib_ticks
        >>> df = get_ib_ticks('SPY')

    Advanced usage:
        >>> df = get_ib_ticks(
        ...     symbol='SPY',
        ...     duration='1 Y',
        ...     barsize='1 day',
        ...     verbose=2,
        ...     show_bars=True
        ... )

Author: [Your Name]
Version: 1.0.0
Date: 2024-02-10
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import pandas as pd
import numpy as np
from datetime import datetime
import time
import threading
import sys
from dotenv import load_dotenv
import os
from typing import Dict, List, Optional, Union
import pytz

# Load environment configuration
load_dotenv(dotenv_path="../.env")

# Default configuration
DEFAULT_CONFIG = {"IB_HOST": "127.0.0.1", "IB_PORT": "4001", "IB_CLIENT_ID": "123"}

# Environment variables with defaults
IB_HOST = os.getenv("IB_HOST", DEFAULT_CONFIG["IB_HOST"])
IB_PORT = int(os.getenv("IB_PORT", DEFAULT_CONFIG["IB_PORT"]))
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", DEFAULT_CONFIG["IB_CLIENT_ID"]))


class MarketDataApp(EWrapper, EClient):
    """
    Main IB API client implementation for market data retrieval.

    This class handles the connection to Interactive Brokers and processes
    incoming market data. It inherits from EWrapper for callback processing
    and EClient for connection management.

    Attributes:
        verbose (int): Verbosity level (0-2)
        show_bars (bool): Whether to display individual bars
        data (dict): Storage for received market data
        done (dict): Request completion status
        connected (bool): Connection status
        connection_tried (bool): Connection attempt status
    """

    def __init__(self, verbose: int = 1, show_bars: bool = False):
        """
        Initialize the market data application.

        Args:
            verbose (int, optional): Verbosity level.
                0: Critical errors only
                1: Main messages (default)
                2: Detailed messages
            show_bars (bool, optional): Display each received bar. Defaults to False.
        """
        EClient.__init__(self, self)
        self.data = {}
        self.done = {}
        self.connected = False
        self.verbose = verbose
        self.show_bars = show_bars
        self.connection_tried = False

        if self.verbose >= 1:
            print("✓ API initialized")

    def error(
        self,
        reqId: int,
        errorCode: int,
        errorString: str,
        advancedOrderRejectJson: str = "",
    ):
        """
        Process error messages from IB API.

        Args:
            reqId (int): Request identifier
            errorCode (int): Error code from IB
            errorString (str): Error description
            advancedOrderRejectJson (str): Advanced rejection info (optional)
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Critical errors are always displayed
        critical_errors = [504, 1100, 1101, 1102, 162, 200, 321]

        if errorCode in critical_errors or self.verbose >= 1:
            if errorCode in [2104, 2106, 2158]:
                if self.verbose >= 2:
                    print(f"🟢 [{current_time}] Data farm connection OK")
            elif errorCode == 2176:
                if self.verbose >= 2:
                    print(
                        f"🟡 [{current_time}] API Version Warning - Fractional shares not supported"
                    )
            else:
                print(f"🔴 [{current_time}] Error {errorCode}: {errorString}")
                if errorCode in [504, 1100, 1101, 1102]:
                    self.connected = False

    def connectAck(self):
        """Handle successful connection acknowledgment."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose >= 1:
            print(f"✓ [{current_time}] Connection acknowledged")
        self.connection_tried = True

    def nextValidId(self, orderId: int):
        """
        Process next valid order ID message.

        Args:
            orderId (int): Next valid order ID
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose >= 1:
            print(f"✓ [{current_time}] Connection established (orderId: {orderId})")
        self.connected = True

    def historicalData(self, reqId: int, bar):
        """
        Process incoming historical data bars.

        Args:
            reqId (int): Request identifier
            bar: Bar data from IB
        """
        if reqId not in self.data:
            self.data[reqId] = []
            if self.verbose >= 1:
                print(f"📊 Starting data reception for reqId {reqId}")

        self.data[reqId].append(
            {
                "Date": bar.date,
                "Open": bar.open,
                "High": bar.high,
                "Low": bar.low,
                "Close": bar.close,
                "Volume": bar.volume,
            }
        )

        if self.show_bars:
            print(f"  → Bar received: {bar.date}")

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """
        Handle completion of historical data request.

        Args:
            reqId (int): Request identifier
            start (str): Start of data period
            end (str): End of data period
        """
        if self.verbose >= 1:
            print(f"✓ Data reception completed for reqId {reqId}")
        self.done[reqId] = True


def format_historical_data(
    dfs: Dict[str, pd.DataFrame], symbol: str, selected_timeframe: str, verbose: int = 1
) -> pd.DataFrame:
    """
    Format historical data into a standardized DataFrame.

    Args:
        dfs (Dict[str, pd.DataFrame]): Dictionary of DataFrames by timeframe
        symbol (str): Trading symbol
        selected_timeframe (str): Selected timeframe
        verbose (int, optional): Verbosity level. Defaults to 1. (minimum 0, maximum 2)


    Returns:
        pd.DataFrame: Formatted DataFrame with standardized columns
    """
    if verbose >= 1:
        print("\n=== Starting data formatting ===")

    formatted_dfs = []

    try:
        for timeframe, df in dfs.items():
            if verbose >= 2:
                print(f"\n📍 Processing timeframe {timeframe}")

            if df is not None and not df.empty:
                if verbose >= 2:
                    print(f"  → Data found: {len(df)} bars")

                df = df.reset_index()
                df["Timestamp"] = df["Date"].astype(np.int64) // 10**6
                df["Ticker"] = symbol
                df["Timeframe"] = timeframe

                # Ensure timezone is preserved
                df = df[
                    [
                        "Ticker",
                        "Timeframe",
                        "Timestamp",
                        "Date",
                        "Timezone",  # Include timezone column
                        "Open",
                        "High",
                        "Low",
                        "Close",
                        "Volume",
                    ]
                ]

                formatted_dfs.append(df)
                if verbose >= 2:
                    print(f"✓ Timeframe {timeframe} processed successfully")
                    print(f"  Timezone: {df['Timezone'].iloc[0]}")

        if formatted_dfs:
            final_df = pd.concat(formatted_dfs, axis=0, ignore_index=True)
            if verbose >= 2:
                print(f"\nTimezones in dataset: {final_df['Timezone'].unique()}")
            return final_df
        return pd.DataFrame()

    except Exception as e:
        print(f"❌ Error during formatting: {str(e)}")
        if verbose >= 2:
            print(f"Stack trace: {sys.exc_info()}")
        return pd.DataFrame()


# def parse_ib_datetime(date_str: str) -> pd.Timestamp:
#     """
#     Parse IB datetime string in multiple formats with any timezone.
#     Args:
#         date_str (str): Date string from IB
#     Returns:
#         pd.Timestamp: Parsed datetime with timezone
#     """
#     try:
#         # Clean the input string
#         date_str = str(date_str).strip()

#         # Split the string into parts
#         parts = date_str.split(' ')

#         # Cas spécifique pour le format intra-journalier (3h)
#         if len(parts) == 2 and '-' in date_str and ':' in date_str:
#             # Format: "2024-11-22 15:30:00-05:00"
#             return pd.to_datetime(date_str)

#         # Handle IB's specific formats:
#         if len(parts) > 3 and ':' in parts[-1]:
#             # Format: "2024-11-22 00:00:00-05:00 US/Eastern"
#             base_dt_str = ' '.join(parts[:-1])  # Take everything except the last part

#             # Check if the last part is a timezone
#             if any(tz_indicator in parts[-1] for tz_indicator in ['/', 'GMT', 'UTC', 'EST', 'EDT']):
#                 tz_str = parts[-1]
#             else:
#                 tz_str = 'US/Eastern'

#             # Parse the base datetime which includes the offset
#             dt = pd.to_datetime(base_dt_str)

#             # If we have a named timezone, convert to it
#             if '/' in tz_str:
#                 try:
#                     timezone = pytz.timezone(tz_str)
#                     dt = dt.tz_convert(timezone)
#                 except pytz.exceptions.UnknownTimeZoneError:
#                     pass  # Keep the original timezone if conversion fails
#             return dt

#         # Standard format handling
#         if len(parts) >= 3:  # Has timezone
#             date_part = f"{parts[0]} {parts[1]}"
#             tz_str = ' '.join(parts[2:])
#         else:
#             date_part = date_str
#             tz_str = 'US/Eastern'

#         # Parse the datetime
#         try:
#             dt = pd.to_datetime(date_part, format='%Y%m%d %H:%M:%S')
#         except ValueError:
#             try:
#                 dt = pd.to_datetime(date_part)
#             except ValueError:
#                 dt = pd.to_datetime(date_part, format='%Y%m%d')

#         # Apply timezone
#         try:
#             timezone = pytz.timezone(tz_str)
#             return timezone.localize(dt)
#         except pytz.exceptions.UnknownTimeZoneError:
#             timezone = pytz.timezone('US/Eastern')
#             return timezone.localize(dt)

#     except Exception as e:
#         print(f"Error parsing date '{date_str}': {str(e)}")
#         raise


def parse_ib_datetime(date_str: str) -> pd.Timestamp:
    """
    Parse IB datetime string in multiple formats without timezone.
    Handles both intraday format (20241024 15:30:00) and daily format (20231124).

    Args:
        date_str (str): Date string from IB
    Returns:
        pd.Timestamp: Parsed datetime
    """
    try:
        # Clean the input string
        date_str = str(date_str).strip()

        # Split the string into parts
        parts = date_str.split(" ")

        if len(parts) == 1:
            # add "  00:00:00"
            parts += ["", "00:00:00"]

        # Format intraday: "20241024 15:30:00"
        date_part = parts[0]
        time_part = parts[2]

        # Parse date and time parts
        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])

        hour = int(time_part[:2])
        minute = int(time_part[3:5])
        second = int(time_part[6:8])

        # Create datetime
        return pd.Timestamp(
            year=year, month=month, day=day, hour=hour, minute=minute, second=second
        )

    except Exception as e:
        print(f"Error parsing date '{date_str}': {str(e)}")
        raise


# Extract timezone from the full datetime string
def parse_ib_timezone(x):
    parts = x.split(" ")
    # Check for offset timezone in the datetime
    if "-" in x or "+" in x:
        return "US/Eastern"  # IB data is in US/Eastern with offset
    # Check for explicit timezone
    if len(parts) >= 3 and "/" in parts[-1]:
        return parts[-1]
    return "US/Eastern"


def get_historical_data(
    symbol: str, timeframe_configs: List[tuple], app: MarketDataApp
) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Retrieve historical data from Interactive Brokers.

    Args:
        symbol (str): Trading symbol
        timeframe_configs (List[tuple]): List of (duration, barsize) configurations
        app (MarketDataApp): Application instance

    Returns:
        Optional[Dict[str, pd.DataFrame]]: Dictionary of DataFrames by timeframe or None on error
    """
    try:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        dataframes = {}

        for idx, (duration, bar_size) in enumerate(timeframe_configs):
            if app.verbose >= 1:
                print(f"\n--- Retrieving {bar_size} data ---")

            reqId = idx + 1
            app.done[reqId] = False

            app.reqHistoricalData(
                reqId=reqId,
                contract=contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=1,
                formatDate=1,
                keepUpToDate=False,
                chartOptions=[],
            )

            timeout = 30
            start_time = time.time()
            while not app.done.get(reqId, False) and time.time() - start_time < timeout:
                time.sleep(0.1)

            if reqId in app.data and app.data[reqId]:
                df = pd.DataFrame(app.data[reqId])
                # Add timezone column first
                df["Timezone"] = df["Date"].apply(parse_ib_timezone)
                # Then parse dates with their respective timezones
                df["Date"] = df["Date"].apply(parse_ib_datetime)
                df.set_index("Date", inplace=True)
                dataframes[bar_size] = df
                if app.verbose >= 1:
                    print(f"✓ {bar_size} data retrieved ({len(df)} bars)")
                    print(f"  Date range: {df.index.min()} to {df.index.max()}")
                    print(f"  Timezones found: {df['Timezone'].unique()}")

            time.sleep(1)

        return dataframes

    except Exception as e:
        print(f"❌ Error during data retrieval: {str(e)}")
        if app.verbose >= 2:
            print(f"Stack trace: {sys.exc_info()}")
        return None


def add_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add an index column to a DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with an index column
    """
    df["Index"] = np.arange(1, len(df) + 1)
    return df


def get_ib_ticks(
    symbol: str,
    duration: str = "1 M",
    barsize: str = "3 hours",
    verbose: int = 1,
    show_bars: bool = False,
    host: Optional[str] = None,
    port: Optional[int] = None,
    client_id: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Main function to retrieve market data from Interactive Brokers.

    Args:
        symbol (str): Trading symbol (e.g., 'SPY')
        duration (str, optional): Historical duration. Defaults to '1 M'.
            Format: 'x S/D/W/M/Y' (Seconds/Days/Weeks/Months/Years)
        barsize (str, optional): Bar size. Defaults to '3 hours'.
            Format: 'x secs/mins/hours/day/week/month'
        verbose (int, optional): Verbosity level. Defaults to 1.
        show_bars (bool, optional): Display individual bars. Defaults to False.
        host (str, optional): IB Gateway host. Defaults to None (uses .env).
        port (int, optional): IB Gateway port. Defaults to None (uses .env).
        client_id (int, optional): Client ID. Defaults to None (uses .env).

    Returns:
        Optional[pd.DataFrame]: DataFrame with historical data or None on error

    Example:
        >>> df = get_ib_ticks('SPY', duration='1 Y', barsize='1 day', verbose=2)
    """
    host = host or IB_HOST
    port = port or IB_PORT
    client_id = client_id or IB_CLIENT_ID

    try:
        current_time = datetime.now().strftime("%Y-%m-d %H:%M:%S")

        if verbose >= 1:
            print(f"\n=== [{current_time}] Starting data retrieval for {symbol} ===")
            print(f"Configuration:")
            print(f"Symbol: {symbol}")
            print(f"Duration: {duration}")
            print(f"Bar size: {barsize}")
            print(f"Connection: {host}:{port} (Client ID: {client_id})")

        timeframe_configs = [
            (duration, barsize),
        ]

        app = MarketDataApp(verbose=verbose, show_bars=show_bars)

        if verbose >= 1:
            print(f"\n📍 [{current_time}] Connecting to IB ({host}:{port})")

        app.connect(host, port, clientId=client_id)

        api_thread = threading.Thread(target=lambda: app.run(), daemon=True)
        api_thread.start()

        timeout = 10
        start_time = time.time()
        while not app.connected and time.time() - start_time < timeout:
            time.sleep(0.1)

        if not app.connected:
            print(
                "❌ Connection closed (could bien be due to timeout or failed request)"
            )
            return None

        dfs = get_historical_data(symbol, timeframe_configs, app)

        if dfs:
            df = format_historical_data(dfs, symbol, barsize, verbose)
            df = add_index(df)

            if not df.empty:

                if verbose >= 1:
                    print(f"\nStatistics:")
                    print(f"Bars: {len(df)}")
                    print(f"Period: {df['Date'].min()} to {df['Date'].max()}")

                if verbose >= 2:
                    print("\nFirst rows:")
                    print(df.head())
                    print("\nLast rows:")
                    print(df.tail())

                return df
            else:
                print("❌ No data available")
                return None
        else:
            print("❌ Data retrieval failed")
            return None

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if verbose >= 2:
            print(f"Stack trace: {sys.exc_info()}")
        return None

    finally:
        if hasattr(app, "disconnect"):
            app.disconnect()
            if verbose >= 1:
                print(f"\n✓ Disconnected")


def get_ib_ticks_multiple(
    symbols: List[str] = ["SPY"],
    timeframes: List[tuple] = [("1 M", "3 hours")],
    verbose: int = 0,
    show_bars: bool = False,
    host: Optional[str] = None,
    port: Optional[int] = None,
    client_id: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Retrieve historical data for multiple symbols and timeframes.

    Args:
        symbols (List[str]): List of symbols to retrieve
        timeframes (List[tuple]): List of (duration, barsize) tuples
        verbose (int): Verbosity level
        show_bars (bool): Whether to show individual bars
        host (Optional[str]): IB Gateway host
        port (Optional[int]): IB Gateway port
        client_id (Optional[int]): Client ID

    Returns:
        Optional[pd.DataFrame]: Combined DataFrame with all data or None on error
    """
    # Environment variables with defaults
    if host is None and verbose >= 1:
        host = os.getenv("IB_HOST", DEFAULT_CONFIG["IB_HOST"])
        print(f"Host: {host}")
    if port is None and verbose >= 1:
        port = int(os.getenv("IB_PORT", DEFAULT_CONFIG["IB_PORT"]))
        print(f"Port: {port}")
    if client_id is None and verbose >= 1:
        client_id = int(os.getenv("IB_CLIENT_ID", DEFAULT_CONFIG["IB_CLIENT_ID"]))
        print(f"Client ID: {client_id}")

    try:
        results = {}
        all_dfs = []

        for symbol in symbols:
            for duration, barsize in timeframes:
                if verbose >= 1:
                    print(f"\nProcessing {symbol} - {barsize} ({duration})")

                df = get_ib_ticks(
                    symbol,
                    duration=duration,
                    barsize=barsize,
                    verbose=verbose,
                    show_bars=show_bars,
                    host=host,
                    port=port,
                    client_id=client_id,
                )

                if df is not None:
                    # Store in results dictionary
                    key = f"{symbol}_{barsize}"
                    results[key] = df
                    all_dfs.append(df)

                    if verbose >= 1:
                        print(f"✓ Added {key} to results: {len(df)} bars")

        if all_dfs:
            # Combine all DataFrames
            final_df = pd.concat(all_dfs, axis=0, ignore_index=True)

            # Sort by date and ticker
            final_df = final_df.sort_values(["Timestamp"], ascending=True)

            if verbose >= 1:
                print("\n=== Final Dataset Statistics ===")
                print(f"Total bars: {len(final_df)}")
                print(f"Symbols: {final_df['Ticker'].unique()}")
                print(f"Timeframes: {final_df['Timeframe'].unique()}")
                print(
                    f"Date range: {final_df['Date'].min()} to {final_df['Date'].max()}"
                )

            return final_df
        else:
            print("❌ No data retrieved")
            return None

    except Exception as e:
        print(f"❌ Error in multi-symbol retrieval: {str(e)}")
        if verbose >= 2:
            print(f"Stack trace: {sys.exc_info()}")
        return None


if __name__ == "__main__":
    """
    Example usage and configuration validation.
    """
    to_csv = False  # Set to True to save combined data to CSV
    verbose = 0  # Verbosity level (0-2)
    show_bars = False  # Show individual bars (True/False)

    # Check and create .env file if not exists
    if not os.path.exists("../.env"):
        print("Creating .env file with default values...")
        with open("../.env", "w") as f:
            f.write(f"IB_HOST={DEFAULT_CONFIG['IB_HOST']}\n")
            f.write(f"IB_PORT={DEFAULT_CONFIG['IB_PORT']}\n")
            f.write(f"IB_CLIENT_ID={DEFAULT_CONFIG['IB_CLIENT_ID']}\n")
        print("✓ .env file created")

    # Display current configuration
    print("\nCurrent configuration:")
    print(f"Host: {IB_HOST}")
    print(f"Port: {IB_PORT}")
    print(f"Client ID: {IB_CLIENT_ID}")
    print(f"Verbose: {verbose}")
    print(f"show_bars: {show_bars}")
    print(f"Save to CSV: {to_csv}")

    print("\n=== Interactive Brokers Historical Data Client ===")

    print("\n🔍 Retrieving historical data for multiple symbols and timeframes...")

    # Example usage with error handling
    try:
        # Basic example
        symbols = ["SPY", "QQQ", "IWM"]
        timeframes = [("1 M", "3 hours"), ("1 Y", "1 day"), ("2 Y", "1 week")]

        print("\nConfiguration:")
        print(f"Symbols: {symbols}")
        print(f"Timeframes: {timeframes}")

        df = get_ib_ticks_multiple(
            symbols=symbols, timeframes=timeframes, verbose=verbose, show_bars=show_bars
        )

        if df is not None:
            print("\nSample of final dataset:")
            print(df.head())
            print(f"\nTotal bars: {len(df)}")
            print("\nStatistics:")
            for symbol in symbols:
                for duration, barsize in timeframes:
                    df_key = df[df["Ticker"] == symbol]
                    df_key = df_key[df_key["Timeframe"] == barsize]
                    print(f"  📍 {symbol} - {barsize} : {len(df_key)} bars")
            print("\n✓ Data retrieval successful")
            if to_csv:
                # Save combined dataset
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"combined_data_{timestamp}.csv"
                df.to_csv(filename, index=False)
                print(f"\n✓ Combined data saved to {filename}")

    except KeyboardInterrupt:
        print("\n\n⚠️ Program interrupted by user")
    except Exception as e:
        print(f"\n❌ Program error: {str(e)}")
    finally:
        print("\n=== Program completed ===")
