import json
import yaml
import logging
import re
from typing import Dict, List, Set, Tuple
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('generate_openapi_crypto.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_json_file(file_path: str) -> Dict:
    """Load and validate a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}: {str(e)}")
        raise

def extract_fields_and_timeframes(metainfo: Dict) -> Tuple[List[Dict], List[str]]:
    """Extract fields and unique timeframes from crypto_metainfo.json."""
    try:
        fields = metainfo.get('body', {}).get('fields', [])
        if not fields:
            logger.warning("No fields found in crypto_metainfo.json")
            return [], []

        field_list = []
        timeframes: Set[str] = set()

        for field in fields:
            name = field.get('n')
            field_type = field.get('t')
            if not name or not field_type:
                logger.warning(f"Skipping invalid field: {field}")
                continue

            # Map TradingView types to OpenAPI types
            type_mapping = {
                'number': 'number',
                'price': 'number',
                'fundamental_price': 'number',
                'percent': 'number',
                'text': 'string',
                'set': 'string',
                'map': 'object',
                'time': 'string'
            }
            openapi_type = type_mapping.get(field_type, 'string')

            # Generate human-readable description
            # Split camelCase or snake_case into words
            words = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ').split()
            description = ' '.join(word.capitalize() for word in words)
            if '|' in name:
                indicator, tf = name.rsplit('|', 1)
                # Clean indicator name for description
                indicator_clean = indicator.replace('.', ' ').replace('_', ' ').title()
                description = f"{indicator_clean} on a {tf} timeframe"

            field_list.append({
                'name': name,
                'type': openapi_type,
                'description': description
            })

            # Extract timeframe if present
            if '|' in name:
                timeframe = name.split('|')[-1]
                # Validate timeframe (e.g., numbers, 1W, 1M, etc.)
                if re.match(r'^\d+$|^1[WDHM]$', timeframe):
                    timeframes.add(timeframe)

        # Define standard timeframes if none found
        if not timeframes:
            timeframes = {'1', '5', '15', '30', '60', '120', '240', '1W', '1M'}
            logger.info("No timeframes found in fields; using default set")

        logger.info(f"Extracted {len(field_list)} fields and {len(timeframes)} timeframes")
        return field_list, sorted(list(timeframes))
    except Exception as e:
        logger.error(f"Error extracting fields and timeframes: {str(e)}")
        raise

def extract_binance_p_tickers(scan: Dict) -> List[str]:
    """Extract Binance .P tickers from crypto_scan.json."""
    try:
        data = scan.get('body', {}).get('data', [])
        total_count = scan.get('body', {}).get('totalCount', 0)
        logger.info(f"Processing {len(data)} tickers from {total_count} total")

        tickers = [
            item.get('s', '')
            for item in data
            if item.get('s', '').startswith('BINANCE:') and item.get('s', '').endswith('.P')
        ]

        if not tickers:
            logger.warning("No Binance .P tickers found; using example tickers")
            tickers = ['BINANCE:BTCUSDT.P', 'BINANCE:ETHUSDT.P']

        return sorted(list(set(tickers)))
    except Exception as e:
        logger.error(f"Error extracting tickers: {str(e)}")
        raise

def generate_openapi_spec(fields: List[Dict], timeframes: List[str], tickers: List[str]) -> Dict:
    """Generate OpenAPI specification."""
    try:
        # Select a subset of fields for the enum
        common_fields = [
            'max_supply', 'market_cap', 'dex_buy_volume_1h', 'dex_sell_volume_1h',
            'RSI|15', 'EMA20|1W', 'crypto_code', 'telegram_members',
            'all_time_high', 'close|1M'
        ]
        enum_fields = [f['name'] for f in fields if f['name'] in common_fields]
        if not enum_fields:
            enum_fields = [f['name'] for f in fields[:10]]  # Fallback to first 10 fields

        spec = {
            'openapi': '3.1.0',
            'info': {
                'title': 'TradingView Crypto Screener API (Binance .P)',
                'description': 'API for accessing cryptocurrency market data from TradingView Screener, focusing on Binance .P tickers.',
                'version': '1.0.0'
            },
            'servers': [
                {'url': 'https://scanner.tradingview.com', 'description': 'Production server'}
            ],
            'components': {
                'securitySchemes': {
                    'ApiKeyAuth': {
                        'type': 'apiKey',
                        'in': 'header',
                        'name': 'X-API-Key'
                    },
                    'CSRFToken': {
                        'type': 'apiKey',
                        'in': 'header',
                        'name': 'X-CSRFToken'
                    }
                }
            },
            'x-fields': fields,
            'x-timeframes': timeframes,
            'paths': {
                '/crypto/scan': {
                    'get': {
                        'summary': 'Retrieve cryptocurrency market data',
                        'description': 'Fetches data for specified fields and Binance .P tickers, with optional timeframe filtering. Refer to x-fields for the complete list of available fields.',
                        'operationId': 'scanCrypto',
                        'security': [
                            {'ApiKeyAuth': [], 'CSRFToken': []}
                        ],
                        'parameters': [
                            {
                                'name': 'fields',
                                'in': 'query',
                                'required': True,
                                'schema': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'string',
                                        'enum': enum_fields
                                    },
                                    'minItems': 1
                                },
                                'description': 'List of fields to retrieve. See x-fields for all available options.',
                                'example': ['close|1M', 'RSI|15', 'market_cap']
                            },
                            {
                                'name': 'tickers',
                                'in': 'query',
                                'required': True,
                                'schema': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'string',
                                        'pattern': '^BINANCE:[A-Z0-9]+\\.P$'
                                    },
                                    'minItems': 1
                                },
                                'description': 'List of Binance .P tickers (e.g., BINANCE:BTCUSDT.P)',
                                'example': ['BINANCE:BTCUSDT.P', 'BINANCE:ETHUSDT.P']
                            },
                            {
                                'name': 'timeframe',
                                'in': 'query',
                                'required': False,
                                'schema': {
                                    'type': 'string',
                                    'enum': timeframes
                                },
                                'description': 'Timeframe for indicators (e.g., 15 for 15 minutes, 1W for 1 week)',
                                'example': '15'
                            }
                        ],
                        'responses': {
                            '200': {
                                'description': 'Successful response with cryptocurrency data',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'data': {
                                                    'type': 'array',
                                                    'items': {
                                                        'type': 'object',
                                                        'properties': {
                                                            'ticker': {
                                                                'type': 'string',
                                                                'description': 'Ticker symbol (e.g., BINANCE:BTCUSDT.P)'
                                                            }
                                                        },
                                                        'additionalProperties': True
                                                    }
                                                },
                                                'totalCount': {
                                                    'type': 'integer',
                                                    'description': 'Total number of records'
                                                }
                                            }
                                        },
                                        'example': {
                                            'data': [
                                                {
                                                    'ticker': 'BINANCE:BTCUSDT.P',
                                                    'close|1M': 65000.0,
                                                    'RSI|15': 70.5,
                                                    'market_cap': 1200000000000
                                                },
                                                {
                                                    'ticker': 'BINANCE:ETHUSDT.P',
                                                    'close|1M': 3500.0,
                                                    'RSI|15': 65.2,
                                                    'market_cap': 420000000000
                                                }
                                            ],
                                            'totalCount': 2
                                        }
                                    }
                                }
                            },
                            '400': {
                                'description': 'Invalid request parameters',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'error': {'type': 'string'}
                                            }
                                        },
                                        'example': {
                                            'error': 'Invalid ticker format'
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        logger.info("Generated OpenAPI specification")
        return spec
    except Exception as e:
        logger.error(f"Error generating OpenAPI spec: {str(e)}")
        raise

def save_openapi_spec(spec: Dict, output_file: str = 'openapi_crypto.yaml') -> None:
    """Save OpenAPI specification to a YAML file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)
        logger.info(f"Saved OpenAPI specification to {output_file}")
    except Exception as e:
        logger.error(f"Error saving OpenAPI spec to {output_file}: {str(e)}")
        raise

def main():
    """Main function to generate OpenAPI specification."""
    try:
        # Load JSON files
        metainfo = load_json_file('crypto_metainfo.json')
        scan = load_json_file('crypto_scan.json')

        # Extract data
        fields, timeframes = extract_fields_and_timeframes(metainfo)
        tickers = extract_binance_p_tickers(scan)

        # Generate and save OpenAPI spec
        spec = generate_openapi_spec(fields, timeframes, tickers)
        save_openapi_spec(spec)

        logger.info("Script completed successfully")
    except Exception as e:
        logger.critical(f"Script failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()
```