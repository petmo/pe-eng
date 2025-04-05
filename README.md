## Logging

The pricing engine uses a colorized logging system for better readability:

- DEBUG messages are shown in cyan
- INFO messages are shown in green
- WARNING messages are shown in yellow
- ERROR messages are shown in red
- CRITICAL messages are shown in red with a white background

You can configure the logging behavior in `config/default.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  use_color: true  # Set to false to disable colored output
```

Try the demo script to see the colored logging in action:

```bash
python log_demo.py
```## Optimization Modes

The pricing engine supports three distinct modes of operation:

### 1. Violation Detection Mode

This mode simply identifies constraint violations without suggesting any price changes:

```bash
python -m pricing_engine.main detect --product-ids P001 P002 P003
```

### 2. Hygiene Optimization Mode

This mode recommends minimal price changes needed to comply with all constraints:

```bash
python -m pricing_engine.main hygiene --product-ids P001 P002 P003
```

### 3. KPI Optimization Mode

This mode optimizes KPIs (profit, revenue, etc.) while respecting constraints:

```bash
python -m pricing_engine.main optimize --product-ids P001 P002 P003 --kpi-weights '{"profit": 0.7, "revenue": 0.3}'
```

> Note: The full KPI optimization mode requires an AI forecasting model for elasticity and demand prediction, which will be implemented in a future version. Currently, it uses a simplified model.# Pricing Engine

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

## Testing

### Local Testing with Dummy Data

For development and testing without a Supabase connection, you can use the included dummy data:

1. Set the configuration to use local data in `config/default.yaml`:

```yaml
data_source:
  use_local: true
  local_data_path: "data/local"
```

The repository includes sample CSV files for testing:
- `data/local/products.csv`: Sample product data
- `data/local/item_groups.csv`: Sample item groups
- `data/local/item_group_members.csv`: Sample group memberships
- `data/local/price_ladder.csv`: Valid prices for the discrete optimization

To run tests with the local data:

```bash
python -m pricing_engine.main check --product-ids P001 P002 P003
```

### API Endpoints

The pricing engine includes Supabase Edge Function endpoints that can be deployed:

- `check_violations`: Run violation detection
- `optimize_prices`: Run price optimization in any of the three modes

Example API request for optimization:

```json
{
  "product_ids": ["P001", "P002", "P003"],
  "mode": "hygiene_optimization",
  "kpi_weights": {"profit": 0.7, "revenue": 0.3}
}
```

Valid `mode` values are:
- `violation_detection` - Only detect violations
- `hygiene_optimization` - Recommend minimal price changes to comply with constraints
- `kpi_optimization` - Optimize KPIs while respecting constraints

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