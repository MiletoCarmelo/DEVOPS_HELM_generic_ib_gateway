from IB import ib_historical as ibh 

### Get historical data ###

symbols = ['SPY']
timeframes = [
    ('3 Y', '1 day'),
    ('3 Y', '1 week'),
]

df = ibh.get_ib_ticks_multiple(
        symbols=symbols,
        timeframes=timeframes,
        verbose=1
    )

# checkpoint :
print(f"columns : ", df.columns)
print(f"nb rows : ", df.shape[0])
print(f"timeframes : ", df['Timeframe'].unique())
print(f"symbol : ", df['Ticker'].unique())
print(f"date range : ", df['Date'].min(), df['Date'].max())