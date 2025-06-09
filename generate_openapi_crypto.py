import json
import yaml
import logging
import re
from typing import Dict, List, Set, Tuple

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
    """Load and validate a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Dictionary containing the parsed JSON data.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be accessed.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {file_path}")
        return data
    except (FileNotFoundError, PermissionError, IOError) as e:
        logger.error(f"Error accessing file {file_path}: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}: {str(e)}")
        raise

def extract_fields_and_timeframes(metainfo: Dict) -> Tuple[List[Dict], List[str]]:
    """Extract fields and unique timeframes from crypto_metainfo.json.

    Args:
        metainfo: Dictionary containing metadata from crypto_metainfo.json.

    Returns:
        Tuple of (list of field metadata, list of timeframes).

    Raises:
        ValueError: If the input data is malformed.
    """
    try:
        fields = metainfo.get('body', {}).get('fields', [])
        if not fields:
            logger.warning("No fields found in crypto_metainfo.json")
            return [], []

        field_list = []
        timeframes: Set[str] = set()
        skipped_fields = 0

        for field in fields:
            name = field.get('n')
            field_type = field.get('t')
            if not name or not field_type:
                skipped_fields += 1
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
            if field_type not in type_mapping:
                logger.warning(f"Unknown field type '{field_type}' for field '{name}'; defaulting to 'string'")
            openapi_type = type_mapping.get(field_type, 'string')

            # Generate human-readable description
            words = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ').split()
            description = ' '.join(word.capitalize() for word in words)
            if '24h' in name.lower():
                description = description.replace('24h', '24-Hour').replace('24H', '24-Hour')
            if 'cmc' in name.lower():
                description = description.replace('Cmc', 'CoinMarketCap').replace('CMC', 'CoinMarketCap')
            if '|' in name:
                indicator, tf = name.rsplit('|', 1)
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
                # Normalize minute-based timeframes (e.g., '15m' → '15')
                if timeframe.endswith('m'):
                    timeframe = timeframe[:-1]
                if re.match(r'^\d+$|^1[WDHM]$', timeframe):
                    timeframes.add(timeframe)

        if skipped_fields:
            logger.info(f"Skipped {skipped_fields} invalid fields")

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
    """Extract Binance .P tickers from crypto_scan.json.

    Args:
        scan: Dictionary containing data from crypto_scan.json.

    Returns:
        List of Binance .P tickers.

    Raises:
        ValueError: If the input data is malformed.
    """
    try:
        data = scan.get('body', {}).get('data', [])
        total_count = scan.get('body', {}).get('totalCount', 0)
        logger.info(f"Processing {len(data)} tickers from {total_count} total")

        if not isinstance(data, list):
            logger.error("Invalid data format in crypto_scan.json: 'data' is not a list")
            return ['BINANCE:BTCUSDT.P', 'BINANCE:ETHUSDT.P']

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
    """Generate an OpenAPI 3.1.0 specification for the TradingView Crypto Screener API.

    Args:
        fields: List of field metadata (name, type, description) from crypto_metainfo.json.
        timeframes: List of unique timeframes extracted from fields.
        tickers: List of Binance .P tickers from crypto_scan.json.

    Returns:
        Dictionary containing the OpenAPI specification.

    Raises:
        ValueError: If critical data (e.g., fields) is missing or invalid.
    """
    try:
        # Select a subset of fields for the enum
        common_fields = [
            'max_supply', 'dex_buy_volume_1h', 'dex_sell_volume_1h',
            'telegram_members', '24h_vol_cmc', 'total_supply',
            'dex_trading_volume_4h', 'all_time_high_day', 'sentiment',
            'in_the_money_addresses_percentage'
        ]
        enum_fields = [f['name'] for f in fields if f['name'] in common_fields]
        if not enum_fields:
            enum_fields = [f['name'] for f in fields[:10]] or ['max_supply', 'telegram_members']
            logger.warning(f"No common fields found; using fallback fields: {enum_fields}")

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
                            {'ApiKeyAuth': []},
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
                                'example': enum_fields[:3] if len(enum_fields) >= 3 else enum_fields
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
                                'example': tickers[:2] if len(tickers) >= 2 else tickers
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
                                'example': timeframes[0] if timeframes else '15'
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
                                                    **{enum_fields[0]: 65000.0 if enum_fields else 'max_supply': 21000000}
                                                },
                                                {
                                                    'ticker': 'BINANCE:ETHUSDT.P',
                                                    **{enum_fields[0]: 3500.0 if enum_fields else 'max_supply': 120000000}
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
    """Save OpenAPI specification to a YAML file.

    Args:
        spec: Dictionary containing the OpenAPI specification.
        output_file: Path to the output YAML file.

    Raises:
        IOError: If the file cannot be written.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)
        logger.info(f"Saved OpenAPI specification to {output_file}")
    except Exception as e:
        logger.error(f"Error saving OpenAPI spec to {output_file}: {str(e)}")
        raise

def main():
    """Main function to generate OpenAPI specification.

    Raises:
        ValueError: If input JSON files are malformed.
        Exception: For other unexpected errors.
    """
    try:
        # Load JSON files
        metainfo = load_json_file('crypto_metainfo.json')
        scan = load_json_file('crypto_scan.json')

        # Validate input structure
        if not metainfo.get('body') or not metainfo.get('body').get('fields'):
            logger.error("Invalid data format in crypto_metainfo.json: missing 'body' or 'fields' key")
            raise ValueError("Invalid input JSON structure in crypto_metainfo.json")
        if not scan.get('body') or not scan.get('body').get('data'):
            logger.error("Invalid data format in crypto_scan.json: missing 'body' or 'data' key")
            raise ValueError("Invalid input JSON structure in crypto_scan.json")

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