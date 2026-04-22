-- 007_apartment_passport.sql
-- Поля реального паспорта квартиры (собирались от заказчика: подъезд, номер кв,
-- коды домофона/сейфа, лицевой счёт ЖКХ, прайс будни/пт-сб).

ALTER TABLE apartments ADD COLUMN entrance TEXT;
ALTER TABLE apartments ADD COLUMN apt_number TEXT;
ALTER TABLE apartments ADD COLUMN intercom_code TEXT;
ALTER TABLE apartments ADD COLUMN safe_code TEXT;
ALTER TABLE apartments ADD COLUMN utility_account TEXT;
ALTER TABLE apartments ADD COLUMN price_weekday INTEGER;
ALTER TABLE apartments ADD COLUMN price_weekend INTEGER;
