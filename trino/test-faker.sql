-- Sample queries to test the faker connector

-- Show available catalogs
SHOW CATALOGS;

-- Show schemas in the faker catalog
SHOW SCHEMAS FROM faker;

-- Show tables in the default schema
SHOW TABLES FROM faker.default;

-- --8<-- [start:create-prices-table]
-- Create a prices table with faker connector
CREATE TABLE faker.default.prices (
  currency VARCHAR NOT NULL WITH (generator = '#{Currency.code}'),
  price DECIMAL(8,2) NOT NULL WITH (min = '0')
);
-- --8<-- [end:create-prices-table]

-- --8<-- [start:create-customer-table]
-- Create a comprehensive customer table
CREATE TABLE faker.default.customer (
  id UUID NOT NULL,
  name VARCHAR NOT NULL WITH (generator = '#{Name.first_name} #{Name.last_name}'),
  email VARCHAR NOT NULL WITH (generator = '#{Internet.emailAddress}'),
  phone VARCHAR NOT NULL WITH (generator = '#{PhoneNumber.phoneNumber}'),
  address VARCHAR NOT NULL WITH (generator = '#{Address.fullAddress}'),
  born_at DATE WITH (min = '1950-01-01', max = '2005-01-01'),
  age_years INTEGER WITH (min = '18', max = '75'),
  group_id INTEGER WITH (allowed_values = ARRAY['10', '32', '81', '99'])
);
-- --8<-- [end:create-customer-table]

-- --8<-- [start:basic-queries]
-- Query the prices table
SELECT * FROM faker.default.prices LIMIT 10;

-- Query the customer table
SELECT * FROM faker.default.customer LIMIT 10;

-- Test the random_string function
SELECT faker.default.random_string('#{Name.first_name}') as first_name;
-- --8<-- [end:basic-queries]

-- --8<-- [start:advanced-queries]
-- Join customer and prices tables
SELECT 
    c.name as customer_name,
    c.email,
    p.currency,
    p.price as order_amount
FROM faker.default.customer c
CROSS JOIN faker.default.prices p
LIMIT 10;

-- Create JSON objects from prices
SELECT JSON_OBJECT(KEY currency VALUE price) AS complex_price
FROM faker.default.prices
LIMIT 5;

-- Sample query to test various generators
SELECT 
    faker.default.random_string('#{Name.fullName}') as full_name,
    faker.default.random_string('#{Internet.emailAddress}') as email,
    faker.default.random_string('#{Address.city}') as city,
    faker.default.random_string('#{Company.name}') as company,
    faker.default.random_string('#{Lorem.sentence}') as description;
-- --8<-- [end:advanced-queries]
