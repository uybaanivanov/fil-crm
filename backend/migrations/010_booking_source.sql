ALTER TABLE bookings ADD COLUMN source TEXT;

UPDATE bookings
SET source = (SELECT source FROM clients WHERE clients.id = bookings.client_id)
WHERE source IS NULL;

ALTER TABLE clients DROP COLUMN source;
