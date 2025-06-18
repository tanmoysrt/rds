-- Remove test database
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

-- Remove anonymous users
DELETE FROM mysql.user WHERE User='';

-- Create root@localhost
CREATE USER IF NOT EXISTS 'root'@'localhost'
  IDENTIFIED VIA mysql_native_password USING '{{ mysql_hashed_root_password }}';
ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING  '{{ mysql_hashed_root_password }}';

-- Create root@127.0.0.1
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1'
  IDENTIFIED VIA mysql_native_password USING '{{ mysql_hashed_root_password }}';
ALTER USER 'root'@'127.0.0.1' IDENTIFIED VIA mysql_native_password USING  '{{ mysql_hashed_root_password }}';

-- Create root@::1 (IPv6 localhost)
CREATE USER IF NOT EXISTS 'root'@'::1'
  IDENTIFIED VIA mysql_native_password USING '{{ mysql_hashed_root_password }}';
ALTER USER 'root'@'::1' IDENTIFIED VIA mysql_native_password USING  '{{ mysql_hashed_root_password }}';

-- Grant all privileges to each root variant
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'::1' WITH GRANT OPTION;

-- Flush again to apply grants
FLUSH PRIVILEGES;

-- NOW safely remove any other root@host combinations
# DELETE FROM mysql.user
# WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- Final flush
# FLUSH PRIVILEGES;
