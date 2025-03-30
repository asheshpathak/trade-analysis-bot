#!/bin/bash

# Script to run stock analysis with extreme rate limiting
# Uses 1 symbol per batch with long waiting periods between batches

# Define batch size
BATCH_SIZE=1  # Process 1 symbol at a time (maximum caution)

# Define delays (in seconds)
HISTORICAL_DELAY=60.0    # 1 minute between historical data API calls
OTHER_DELAY=2.0          # 2 seconds between other API calls
RETRY_DELAY=240.0        # 4 minutes when rate limited
MAX_RETRIES=3
BETWEEN_BATCH_DELAY=120  # 2 minutes between batches

# Options file
OPTIONS_FILE="Options_Companies.txt"

# Check if options file exists
if [ ! -f "$OPTIONS_FILE" ]; then
    echo "Error: Options file $OPTIONS_FILE not found!"
    exit 1
fi

# Create cache directories
mkdir -p output/historical_cache
mkdir -p output/cache

# Initial cooldown period
INITIAL_COOLDOWN=300  # 5 minutes to reset any rate limits
echo "Starting with ${INITIAL_COOLDOWN}s cooldown to reset any rate limits..."
sleep $INITIAL_COOLDOWN

# Read symbols from file
SYMBOLS=$(cat "$OPTIONS_FILE" | tr ',' ' ')
read -ra SYMBOLS_ARRAY <<< "$SYMBOLS"
TOTAL_SYMBOLS=${#SYMBOLS_ARRAY[@]}

echo "==========================================="
echo "EXTREME RATE LIMITED ANALYSIS"
echo "==========================================="
echo "Found $TOTAL_SYMBOLS symbols in $OPTIONS_FILE"
echo "Processing 1 symbol at a time with long pauses"
echo "Historical delay: ${HISTORICAL_DELAY}s"
echo "Other delay: ${OTHER_DELAY}s"
echo "Retry delay: ${RETRY_DELAY}s"
echo "Between batch delay: ${BETWEEN_BATCH_DELAY}s"
echo "==========================================="

# Process symbols one by one
for ((i=0; i<TOTAL_SYMBOLS; i++)); do
    SYMBOL=${SYMBOLS_ARRAY[$i]}

    echo "==========================================="
    echo "PROCESSING SYMBOL $((i+1)) of $TOTAL_SYMBOLS: $SYMBOL"
    echo "==========================================="

    # Run analysis for single symbol
    python main.py --analyze \
        --symbols "$SYMBOL" \
        --historical-delay $HISTORICAL_DELAY \
        --other-delay $OTHER_DELAY \
        --retry-delay $RETRY_DELAY \
        --max-retries $MAX_RETRIES

    # Continue to next symbol if this is not the last one
    if [ $((i + 1)) -lt $TOTAL_SYMBOLS ]; then
        echo "==========================================="
        echo "Waiting ${BETWEEN_BATCH_DELAY}s before next symbol..."
        echo "==========================================="
        sleep $BETWEEN_BATCH_DELAY
    fi
done

echo "==========================================="
echo "Analysis completed for all symbols!"
echo "==========================================="