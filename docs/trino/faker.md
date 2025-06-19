# Faker Connector

This guide covers how to use the faker connector in Trino to generate realistic fake data for testing and development purposes.

## Overview

The faker connector uses the [Datafaker library](https://www.datafaker.net/documentation/providers/) to generate realistic fake data. It's perfect for:

- Testing queries with realistic data
- Data pipeline development
- Performance testing
- Demo environments

## Configuration

The faker connector is configured with the following settings:

```yaml title="trino/values-template.yaml"
--8<-- "trino/values-template.yaml:catalogs"
```

Here's a breakdown of the configuration:

- `connector.name=faker`: Specifies the faker connector
- `faker.null-probability=0.1`: 10% chance of null values in generated data
- `faker.default-limit=1000`: Default row limit for queries
- `faker.locale=en`: English locale for generated data patterns

## Creating Tables

The faker connector requires you to create tables with specific generator expressions:

### 1. Prices Table

```sql title="test-faker.sql - Prices Table"
--8<-- "trino/test-faker.sql:create-prices-table"
```

### 2. Customer Table

```sql title="test-faker.sql - Customer Table"
--8<-- "trino/test-faker.sql:create-customer-table"
```

## Example Queries

### Basic Data Generation

```sql title="test-faker.sql - Basic Queries"
--8<-- "trino/test-faker.sql:basic-queries"
```

### Advanced Queries

```sql title="test-faker.sql - Advanced Queries"
--8<-- "trino/test-faker.sql:advanced-queries"
```

## Testing Commands

Run individual queries from the command line:

```bash
kubectl exec -it deployment/trino-coordinator --namespace trino -- trino --execute "SHOW TABLES FROM faker.default;"
kubectl exec -it deployment/trino-coordinator --namespace trino -- trino --execute "SELECT * FROM faker.default.customer LIMIT 5;"
```

## Available Faker Tables

The faker connector has been tested and verified with these tables:

- [x] `prices` - Currency codes and decimal prices (created and tested)
- [x] `customer` - Customer profiles with realistic data (created and tested)

## Faker Functions

- [x] `random_string()` - Generate custom fake data using Datafaker expressions

## Available Generators

The faker connector supports numerous generators from the Datafaker library:

### Personal Information
- `#{Name.firstName}`, `#{Name.lastName}`, `#{Name.fullName}`
- `#{Internet.emailAddress}`, `#{PhoneNumber.phoneNumber}`
- `#{Address.fullAddress}`, `#{Address.city}`, `#{Address.country}`

### Business Data
- `#{Currency.code}`, `#{Company.name}`
- `#{Commerce.productName}`, `#{Commerce.price}`

### Text Content
- `#{Lorem.sentence}`, `#{Lorem.paragraph}`
- `#{Lorem.words}`, `#{Lorem.characters}`

### Dates and Numbers
- `#{Date.past}`, `#{Date.future}`
- `#{Number.randomDouble}`, `#{Number.randomLong}`

### Financial Data
- `#{Finance.creditCard}`, `#{Finance.iban}`
- `#{Finance.bic}`, `#{Finance.stockTicker}`

For a complete list of available generators, see the [Datafaker Documentation](https://www.datafaker.net/documentation/providers/).

## Column Constraints

You can apply various constraints to faker columns:

### Value Ranges
```sql
-- Numeric ranges
age INTEGER WITH (min = '18', max = '75')
price DECIMAL(8,2) WITH (min = '0', max = '1000')

-- Date ranges  
birth_date DATE WITH (min = '1950-01-01', max = '2005-01-01')
```

### Allowed Values
```sql
-- Specific allowed values
status VARCHAR WITH (allowed_values = ARRAY['active', 'inactive', 'pending'])
priority INTEGER WITH (allowed_values = ARRAY['1', '2', '3', '4', '5'])
```

### Null Probability
```sql
-- Override default null probability for specific columns
optional_field VARCHAR WITH (generator = '#{Lorem.word}', null_probability = '0.3')
```

## Best Practices

1. **Use Appropriate Data Types**: Match your production schema data types
2. **Set Realistic Constraints**: Use min/max values that make sense for your domain
3. **Consider Cardinality**: Use allowed_values for categorical data
4. **Test Join Performance**: Cross joins can generate large result sets quickly
5. **Limit Result Sets**: Always use LIMIT in development to avoid overwhelming queries

## Common Use Cases

### E-commerce Data
```sql
CREATE TABLE faker.default.products (
  id UUID NOT NULL,
  name VARCHAR NOT NULL WITH (generator = '#{Commerce.productName}'),
  category VARCHAR WITH (allowed_values = ARRAY['electronics', 'clothing', 'books', 'home']),
  price DECIMAL(10,2) WITH (min = '1.00', max = '999.99'),
  description VARCHAR WITH (generator = '#{Lorem.sentence}'),
  in_stock BOOLEAN NOT NULL
);
```

### User Analytics
```sql
CREATE TABLE faker.default.user_events (
  user_id UUID NOT NULL,
  event_type VARCHAR WITH (allowed_values = ARRAY['login', 'logout', 'purchase', 'view']),
  timestamp TIMESTAMP NOT NULL,
  session_id VARCHAR WITH (generator = '#{Internet.uuid}'),
  ip_address VARCHAR WITH (generator = '#{Internet.ipV4Address}')
);
```

### Financial Transactions
```sql
CREATE TABLE faker.default.transactions (
  transaction_id UUID NOT NULL,
  account_number VARCHAR WITH (generator = '#{Finance.iban}'),
  amount DECIMAL(12,2) WITH (min = '-10000', max = '10000'),
  currency VARCHAR WITH (generator = '#{Currency.code}'),
  transaction_date DATE WITH (min = '2020-01-01', max = '2024-12-31'),
  merchant VARCHAR WITH (generator = '#{Company.name}')
);
```
