-- ============================================================
-- Sky Motors — Inventory Schema & Queries
-- ============================================================
-- Currently the bot loads inventory from data/Active Inventory.csv.
-- When ready to move to DB, run the CREATE TABLE below and
-- use the upsert query to import the CSV.
-- ============================================================


-- ------------------------------------------------------------
-- SCHEMA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS skymotors.inventory (
    id              SERIAL          PRIMARY KEY,
    stock_number    VARCHAR(20)     UNIQUE NOT NULL,
    vin             VARCHAR(20),
    description     TEXT            NOT NULL,
    year            INTEGER,
    make            VARCHAR(50),
    model           VARCHAR(100),
    color           VARCHAR(50),
    mileage         INTEGER,
    -- selling price (AdvertisingPrice or VehiclePrice from DMS)
    price           NUMERIC(10,2),
    -- market reference values from DMS BookValue columns
    book_low        NUMERIC(10,2),  -- BookValue2 (floor)
    book_high       NUMERIC(10,2),  -- BookValue3 (high)
    -- status
    status          VARCHAR(50)     DEFAULT 'IN INVENTORY',
    custom_status   VARCHAR(50),    -- e.g. 'SOLD'
    no_price        BOOLEAN         DEFAULT FALSE,
    days_in_stock   INTEGER         DEFAULT 0,
    date_in_stock   DATE,
    purchase_type   VARCHAR(50),    -- 'TRADE-IN', 'AUCTION', etc.
    -- metadata
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inv_status  ON skymotors.inventory (status, custom_status);
CREATE INDEX IF NOT EXISTS idx_inv_make    ON skymotors.inventory (LOWER(make));
CREATE INDEX IF NOT EXISTS idx_inv_price   ON skymotors.inventory (price);
CREATE INDEX IF NOT EXISTS idx_inv_search  ON skymotors.inventory
    USING gin(to_tsvector('english', description));


-- ------------------------------------------------------------
-- QUERIES
-- ------------------------------------------------------------

-- 1. All available, priced vehicles
SELECT stock_number, description, year, make, model, color, mileage, price, days_in_stock
FROM skymotors.inventory
WHERE status = 'IN INVENTORY'
  AND (custom_status IS NULL OR UPPER(custom_status) != 'SOLD')
  AND price > 0
ORDER BY price ASC;


-- 2. Full-text search by keyword (make/model/trim)
--    Replace :query with the customer's input, e.g. 'honda civic'
SELECT stock_number, description, year, make, model, color, mileage, price
FROM skymotors.inventory
WHERE status = 'IN INVENTORY'
  AND (custom_status IS NULL OR UPPER(custom_status) != 'SOLD')
  AND to_tsvector('english', LOWER(description)) @@ plainto_tsquery('english', :query)
ORDER BY (price > 0) DESC, price ASC
LIMIT 5;


-- 3. Simple LIKE search (fallback / partial match)
SELECT stock_number, description, year, make, model, color, mileage, price
FROM skymotors.inventory
WHERE status = 'IN INVENTORY'
  AND (custom_status IS NULL OR UPPER(custom_status) != 'SOLD')
  AND LOWER(description) LIKE '%' || LOWER(:keyword) || '%'
ORDER BY (price > 0) DESC, price ASC
LIMIT 5;


-- 4. Filter by max budget
SELECT stock_number, description, year, make, model, color, mileage, price
FROM skymotors.inventory
WHERE status = 'IN INVENTORY'
  AND (custom_status IS NULL OR UPPER(custom_status) != 'SOLD')
  AND (price > 0 AND price <= :max_price
       OR price = 0 AND book_low <= :max_price)   -- include unpriced if book_low fits
ORDER BY (price > 0) DESC, price ASC
LIMIT 5;


-- 5. Keyword + budget combined
SELECT stock_number, description, year, make, model, color, mileage, price
FROM skymotors.inventory
WHERE status = 'IN INVENTORY'
  AND (custom_status IS NULL OR UPPER(custom_status) != 'SOLD')
  AND LOWER(description) LIKE '%' || LOWER(:keyword) || '%'
  AND (price > 0 AND price <= :max_price
       OR price = 0 AND book_low <= :max_price)
ORDER BY (price > 0) DESC, price ASC
LIMIT 5;


-- 6. Vehicles without a selling price set (for internal repricing review)
SELECT stock_number, description, mileage, book_low, book_high, days_in_stock
FROM skymotors.inventory
WHERE status = 'IN INVENTORY'
  AND (custom_status IS NULL OR UPPER(custom_status) != 'SOLD')
  AND (price IS NULL OR price = 0)
ORDER BY days_in_stock DESC;


-- 7. Lead + inventory cross-reference (which leads match available stock)
SELECT
    l.phone,
    l.name,
    l.interest,
    l.vehicle_interest,
    l.budget,
    l.created_at,
    i.description   AS matched_vehicle,
    i.price         AS matched_price,
    i.stock_number
FROM skymotors.leads l
LEFT JOIN skymotors.inventory i
    ON LOWER(i.description) LIKE
       '%' || LOWER(SPLIT_PART(l.vehicle_interest, ' ', 2)) || '%'
   AND (custom_status IS NULL OR UPPER(i.custom_status) != 'SOLD')
ORDER BY l.created_at DESC;


-- ------------------------------------------------------------
-- UPSERT — import / sync from CSV or DMS export
-- ------------------------------------------------------------
INSERT INTO skymotors.inventory (
    stock_number, vin, description, year, make, model, color, mileage,
    price, book_low, book_high, status, custom_status, no_price,
    days_in_stock, date_in_stock, purchase_type, updated_at
) VALUES (
    :stock_number, :vin, :description, :year, :make, :model, :color, :mileage,
    :price, :book_low, :book_high, :status, :custom_status, :no_price,
    :days_in_stock, :date_in_stock, :purchase_type, NOW()
)
ON CONFLICT (stock_number) DO UPDATE SET
    vin           = EXCLUDED.vin,
    description   = EXCLUDED.description,
    color         = EXCLUDED.color,
    mileage       = EXCLUDED.mileage,
    price         = EXCLUDED.price,
    book_low      = EXCLUDED.book_low,
    book_high     = EXCLUDED.book_high,
    status        = EXCLUDED.status,
    custom_status = EXCLUDED.custom_status,
    no_price      = EXCLUDED.no_price,
    days_in_stock = EXCLUDED.days_in_stock,
    updated_at    = NOW();
