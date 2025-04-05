# Pricing Engine

A Python-based pricing optimization engine that enforces item relationship constraints and can optimize prices based on business rules.

## Features

- Violation detection for price relationships
- Support for different constraint types:
  - Equal price groups
  - Good-better-best pricing rules
  - Better value for bigger packs
- Hygiene checks to ensure price compliance
- Optimization to suggest new prices that satisfy all constraints
- Integration with Supabase for data storage

## Installation

1. Clone the repository
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The application uses a combination of YAML configuration files for business logic and environment variables for sensitive credentials.

### Environment Variables (for sensitive data)

1. Copy the example environment file and set your values:

```bash
cp .env.example .env
```

2. Edit the `.env` file to include your Supabase credentials:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-api-key
```

You can also set the logging level through environment variables:

```
LOG_LEVEL=INFO
```

### YAML Configuration (for business parameters)

Business parameters and logic configuration are stored in `config/default.yaml`. These include:

- Price ladder configuration
- Price change constraints (min/max percentages)
- Table names
- Logging format

To modify these parameters, edit the YAML file directly.

## Usage

### Command Line Interface

Check for violations:

```bash
python -m pricing_engine.main check --product-ids PRODUCT1 PRODUCT2 --output results.json
```

Optimize prices:

```bash
python -m pricing_engine.main optimize --product-ids PRODUCT1 PRODUCT2 --output results.json
```

### API Integration

The pricing engine includes Supabase Edge Function endpoints that can be deployed:

- `check_violations`: Check if products violate any constraints
- `optimize_prices`: Run optimization to get new prices that comply with constraints

## Development

### Project Structure

```
pricing_engine/
├── config/           # Configuration
├── data/             # Data loading and schemas
├── optimization/     # Optimization engine
│   ├── constraints/  # Pricing constraints
├── api/              # API endpoints
├── utils/            # Utilities
```

## License

[MIT License](LICENSE)