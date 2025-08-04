def calculate_rsi(prices, period=14):
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        return 100  # RSI maxed out
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return calculate_rsi()
