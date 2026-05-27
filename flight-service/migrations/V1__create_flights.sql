CREATE TABLE flights (
    id UUID PRIMARY KEY,
    flight_number VARCHAR(16) NOT NULL UNIQUE,
    origin CHAR(3) NOT NULL,
    destination CHAR(3) NOT NULL,
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ NOT NULL,
    total_seats INTEGER NOT NULL CHECK (total_seats > 0),
    available_seats INTEGER NOT NULL CHECK (available_seats >= 0 AND available_seats <= total_seats),
    price NUMERIC(12, 2) NOT NULL CHECK (price > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('SCHEDULED', 'CANCELLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (origin <> destination),
    CHECK (arrival_time > departure_time)
);

CREATE INDEX idx_flights_route ON flights (origin, destination, status);

CREATE TABLE seat_reservations (
    id UUID PRIMARY KEY,
    booking_id UUID NOT NULL UNIQUE,
    flight_id UUID NOT NULL REFERENCES flights(id),
    seat_count INTEGER NOT NULL CHECK (seat_count > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'RELEASED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
