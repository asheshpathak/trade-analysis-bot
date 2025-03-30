# Stock Analysis Application

A comprehensive stock analysis application that computes a wide range of metrics and outputs data in both CSV and JSON formats. This application integrates with market data sources using the Zerodha Kite API for authentication and data fetching.

## Features

- **Advanced Stock Analysis**: Calculates technical indicators, price targets, support/resistance levels, and more
- **Option Analysis**: Analyzes option chains and provides option trading recommendations
- **Real-time Data**: Integrates with Zerodha Kite API for live market data
- **Multiple Output Formats**: Generates structured CSV and JSON outputs
- **API Integration**: Provides RESTful API endpoints for web application integration
- **Concurrent Processing**: Uses multithreading and parallel processing for optimal performance
- **Market-Aware Operation**: Adjusts behavior based on market status (open/closed)
- **Robust Logging**: Comprehensive logging system for operational monitoring

## Project Structure

```
stock_analysis/
│
├── config/               # Configuration settings
├── core/                 # Core application components
│   ├── auth/             # Authentication modules
│   ├── data/             # Data fetching and processing
│   ├── analysis/         # Analysis algorithms
│   └── output/           # Output generation
├── api/                  # API endpoints
├── utils/                # Utility functions
├── logs/                 # Log files
├── output/               # Output files
├── tests/                # Test suite
├── main.py               # Entry point
├── requirements.txt      # Dependencies
├── Dockerfile            # Docker configuration
└── docker-compose.yml    # Docker Compose configuration
```

## Prerequisites

- Python 3.10 or higher
- Zerodha Kite API credentials

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/stock-analysis.git
   cd stock-analysis
   ```

2. Create a `.env` file with your Zerodha API credentials:
   ```
   ZERODHA_API_KEY=your_api_key
   ZERODHA_API_SECRET=your_api_secret
   ZERODHA_USER_ID=your_user_id
   ZERODHA_PASSWORD=your_password
   ```

3. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/stock-analysis.git
   cd stock-analysis
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Zerodha API credentials.

4. Run the application:
   ```bash
   python main.py --api  # Run as API server
   # OR
   python main.py --analyze  # Run one-time analysis
   # OR
   python main.py --periodic --interval 3600  # Run periodic analysis
   ```

## Usage

### Command Line Arguments

- `--api`: Run as API server
- `--analyze`: Run analysis once
- `--periodic`: Run periodic analysis
- `--symbols`: Stock symbols to analyze (space-separated)
- `--interval`: Update interval in seconds for periodic analysis
- `--no-csv`: Disable CSV output
- `--no-json`: Disable JSON output

### API Endpoints

The API server runs on port 8000 by default and provides the following endpoints:

- `GET /api/v1/health`: Health check endpoint
- `GET /api/v1/market/status`: Get current market status
- `GET /api/v1/stocks`: Get list of available stocks
- `GET /api/v1/analysis/{symbol}`: Get analysis for a single stock
- `POST /api/v1/analysis/batch`: Analyze multiple stocks
- `GET /api/v1/analysis/latest`: Get latest analysis results
- `GET /api/v1/indicators/{symbol}`: Get technical indicators for a stock
- `GET /api/v1/options/{symbol}`: Get option chain for a stock

API documentation is available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Output Format

### CSV Output

The CSV output includes comprehensive data with columns arranged in logical sections:

- Basic Stock Information (symbol, previous close, current price, etc.)
- Signal Information (signal, direction, confidence, etc.)
- Price Targets (target price, stop loss, risk/reward ratio, etc.)
- Technical Indicators (trend score, momentum score, RSI, MACD, etc.)
- Support and Resistance Levels
- Position Sizing Recommendations
- Option Information (strike, IV percentile, max pain, etc.)
- Option Prices (current, target, stop loss)
- Risk Factors (earnings impact, days to earnings)
- Model Metadata (accuracy, timestamp)

### JSON Output

The JSON output is structured with nested sections for better organization:

```json
{
  "metadata": {
    "generated_at": "2025-03-29 12:34:56",
    "version": "1.0.0"
  },
  "stocks": [
    {
      "basic_info": { ... },
      "signal_info": { ... },
      "price_targets": { ... },
      "technical_indicators": { ... },
      "support_resistance": { ... },
      "position_sizing": { ... },
      "option_info": { ... },
      "option_prices": { ... },
      "risk_factors": { ... },
      "metadata": { ... }
    }
  ]
}
```

## Future Web App Integration

The application provides API endpoints for easy integration with a future React web application. The application handles two scenarios:

1. **Market Closed**: Sends the most recent data
2. **Market Open**: Displays current positions and triggers alerts for trade entries/exits

Follow these steps for web app integration:

1. Connect to API endpoints using provided route documentation
2. Implement authentication if needed
3. Use WebSockets or polling for live updates
4. Implement alert system for trade notifications

## Deployment

### Docker Deployment

For production deployment:

1. Update the `.env` file with production credentials
2. Adjust Docker Compose settings if needed
3. Build and deploy:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

### Cloud Deployment

For AWS deployment:

1. Create an EC2 instance
2. Install Docker and Docker Compose
3. Clone the repository and configure environment variables
4. Build and run the Docker containers
5. Configure security groups to expose required ports

## License

This project is licensed under the MIT License.