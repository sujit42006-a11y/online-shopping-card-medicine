CREATE DATABASE IF NOT EXISTS medikart CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE medikart;

DROP TABLE IF EXISTS payments, prescriptions, order_items, orders, cart_items, cart, addresses, medicines, categories, users;

CREATE TABLE users (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(120) NOT NULL,
 email VARCHAR(160) NOT NULL UNIQUE,
 phone VARCHAR(30),
 password_hash VARCHAR(255) NOT NULL,
 role ENUM('customer','admin') NOT NULL DEFAULT 'customer',
 is_active TINYINT(1) NOT NULL DEFAULT 1,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 INDEX idx_users_role(role)
);

CREATE TABLE categories (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(100) NOT NULL UNIQUE,
 description VARCHAR(255),
 is_active TINYINT(1) NOT NULL DEFAULT 1
);

CREATE TABLE medicines (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(160) NOT NULL,
 brand VARCHAR(120) NOT NULL,
 generic_name VARCHAR(160),
 category_id INT NOT NULL,
 price DECIMAL(10,2) NOT NULL,
 discount DECIMAL(10,2) NOT NULL DEFAULT 0,
 stock INT NOT NULL DEFAULT 0,
 pack_size VARCHAR(80),
 description TEXT,
 manufacturer VARCHAR(160),
 image VARCHAR(255),
 prescription_required TINYINT(1) NOT NULL DEFAULT 0,
 is_active TINYINT(1) NOT NULL DEFAULT 1,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(category_id) REFERENCES categories(id),
 INDEX idx_medicine_name(name),
 INDEX idx_medicine_category(category_id)
);

CREATE TABLE addresses (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 label VARCHAR(50) NOT NULL,
 line1 VARCHAR(255) NOT NULL,
 city VARCHAR(100) NOT NULL,
 state VARCHAR(100) NOT NULL,
 pincode VARCHAR(20) NOT NULL,
 phone VARCHAR(30) NOT NULL,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE cart (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL UNIQUE,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE cart_items (
 id INT AUTO_INCREMENT PRIMARY KEY,
 cart_id INT NOT NULL,
 medicine_id INT NOT NULL,
 quantity INT NOT NULL,
 UNIQUE KEY uq_cart_medicine(cart_id,medicine_id),
 FOREIGN KEY(cart_id) REFERENCES cart(id) ON DELETE CASCADE,
 FOREIGN KEY(medicine_id) REFERENCES medicines(id)
);

CREATE TABLE orders (
 id INT AUTO_INCREMENT PRIMARY KEY,
 order_number VARCHAR(40) NOT NULL UNIQUE,
 user_id INT NOT NULL,
 address TEXT NOT NULL,
 phone VARCHAR(30) NOT NULL,
 payment_method ENUM('COD','Demo Payment') NOT NULL DEFAULT 'COD',
 subtotal DECIMAL(10,2) NOT NULL,
 discount DECIMAL(10,2) NOT NULL DEFAULT 0,
 delivery_charge DECIMAL(10,2) NOT NULL DEFAULT 0,
 total DECIMAL(10,2) NOT NULL,
 status ENUM('Pending','Prescription Verification','Confirmed','Packed','Shipped','Out for Delivery','Delivered','Cancelled') NOT NULL DEFAULT 'Pending',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id),
 INDEX idx_orders_user(user_id),
 INDEX idx_orders_status(status)
);

CREATE TABLE order_items (
 id INT AUTO_INCREMENT PRIMARY KEY,
 order_id INT NOT NULL,
 medicine_id INT,
 medicine_name VARCHAR(160) NOT NULL,
 quantity INT NOT NULL,
 unit_price DECIMAL(10,2) NOT NULL,
 FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
 FOREIGN KEY(medicine_id) REFERENCES medicines(id)
);

CREATE TABLE prescriptions (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 filename VARCHAR(255) NOT NULL,
 original_name VARCHAR(255) NOT NULL,
 status ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
 reviewed_by INT NULL,
 reviewed_at DATETIME NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id),
 FOREIGN KEY(reviewed_by) REFERENCES users(id),
 INDEX idx_prescription_status(status)
);

CREATE TABLE payments (
 id INT AUTO_INCREMENT PRIMARY KEY,
 order_id INT NOT NULL,
 method ENUM('COD','Demo Payment') NOT NULL,
 status ENUM('Pending','Paid','Failed') NOT NULL DEFAULT 'Pending',
 amount DECIMAL(10,2) NOT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

INSERT INTO categories(name,description) VALUES
('Pain Relief','Demo products for the pain relief category.'),
('Cold & Cough','Demo products for cold and cough category.'),
('Vitamins','Fictional/demo vitamin products.'),
('Digestive Care','Demo digestive care products.'),
('First Aid','Basic first-aid products.'),
('Personal Care','Personal care products.');

INSERT INTO medicines(name,brand,generic_name,category_id,price,discount,stock,pack_size,description,manufacturer,prescription_required) VALUES
('ReliefMax 500','MediKart Labs','Demo Paracetamol',1,80,5,100,'10 tablets','Fictional demo medicine record. Follow product labeling and professional advice.','MediKart Labs',0),
('ColdEase Syrup','HealthDemo','Demo Cold Formula',2,120,10,60,'100 ml','Fictional demo product record.','HealthDemo Pvt Ltd',0),
('VitaPlus Tablets','NutriDemo','Demo Multivitamin',3,220,20,75,'30 tablets','Fictional demo vitamin product.','NutriDemo',0),
('DigestCare 20','CareLab','Demo Digestive Product',4,150,15,50,'10 capsules', 'Fictional demo medicine record.', 'CareLab',1),
('FirstAid Antiseptic','SafeCare','Demo Antiseptic',5,95,0,80,'100 ml','Fictional demo first-aid product.','SafeCare',0),
('DailyCare Lotion','WellnessDemo','Demo Skin Care',6,180,10,40,'100 g','Fictional demo personal-care product.','WellnessDemo',0);

-- Create an admin using the app so the password is securely hashed:
-- python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Admin@123'))"
-- Then:
-- INSERT INTO users(name,email,password_hash,role) VALUES
-- ('MediKart Admin','admin@medikart.local','PASTE_HASH_HERE','admin');
