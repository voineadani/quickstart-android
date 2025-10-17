# Hunting Data System - Setup Guide

This guide provides step-by-step instructions for setting up the Hunting Data System backend using either Docker Compose or XAMPP.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option 1: Docker Compose Setup](#option-1-docker-compose-setup)
3. [Option 2: XAMPP Setup](#option-2-xampp-setup)
4. [Database Setup](#database-setup)
5. [Testing the Installation](#testing-the-installation)
6. [Common Issues](#common-issues)

---

## Prerequisites

### General Requirements
- PHP 8.2 or higher
- Composer 2.x
- MySQL 8.0 or higher
- Git

### For Docker Setup
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+

### For XAMPP Setup
- XAMPP 8.2+ (includes PHP 8.2+ and MySQL 8.0+)
- Available from: https://www.apachefriends.org/

---

## Option 1: Docker Compose Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/voineadani/quickstart-android.git
cd quickstart-android
```

### Step 2: Configure Environment

```bash
cd backend
cp .env.example .env
```

Edit `.env` file with Docker database credentials:

```env
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=hunting_data_system
DB_USERNAME=hunting_user
DB_PASSWORD=hunting_password
```

### Step 3: Build and Start Containers

```bash
cd ..  # Back to project root
docker-compose up -d
```

This will start three containers:
- `hunting_data_app` - PHP-FPM application
- `hunting_data_nginx` - Nginx web server
- `hunting_data_db` - MySQL 8.0 database

### Step 4: Install Dependencies and Setup

```bash
# Enter the application container
docker exec -it hunting_data_app bash

# Inside container:
composer install
php artisan key:generate
php artisan migrate
php artisan db:seed
php artisan telescope:install
php artisan storage:link

# Exit container
exit
```

### Step 5: Access the Application

The API is now available at: **http://localhost:8000**

Test with:
```bash
curl http://localhost:8000/up
```

---

## Option 2: XAMPP Setup

### Step 1: Install XAMPP

Download and install XAMPP from https://www.apachefriends.org/

Ensure you install:
- Apache
- MySQL
- PHP 8.2+

### Step 2: Clone Repository to htdocs

```bash
cd /path/to/xampp/htdocs
git clone https://github.com/voineadani/quickstart-android.git hunting-data-system
cd hunting-data-system/backend
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file:

```env
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=hunting_data_system
DB_USERNAME=root
DB_PASSWORD=          # Leave empty or use your MySQL root password
```

### Step 4: Create Database

1. Start XAMPP Control Panel
2. Start Apache and MySQL services
3. Open phpMyAdmin: http://localhost/phpmyadmin
4. Create new database: `hunting_data_system`

### Step 5: Install Dependencies

```bash
composer install
php artisan key:generate
php artisan migrate
php artisan db:seed
php artisan telescope:install
php artisan storage:link
```

### Step 6: Configure Apache Virtual Host (Optional)

Create a virtual host for cleaner URLs:

Edit `httpd-vhost.conf` in XAMPP:

```apache
<VirtualHost *:80>
    ServerName hunting-data.local
    DocumentRoot "/path/to/xampp/htdocs/hunting-data-system/backend/public"
    <Directory "/path/to/xampp/htdocs/hunting-data-system/backend/public">
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

Add to hosts file (`C:\Windows\System32\drivers\etc\hosts` on Windows):
```
127.0.0.1 hunting-data.local
```

Restart Apache and access at: **http://hunting-data.local**

---

## Database Setup

### Running Migrations

Migrations create all necessary database tables:

```bash
php artisan migrate
```

### Seeding Demo Data

Seed the database with demo roles, labs, and users:

```bash
php artisan db:seed
```

This creates:
- **3 Roles**: HUNTER, LAB, ADMIN
- **2 Labs**: Central Testing Laboratory, Regional Veterinary Lab
- **3 Users**:
  - Admin (email: admin@hunting-data.example.com, password: password)
  - Hunter (email: john.hunter@example.com, password: password)
  - Lab Tech (email: lab.tech@central-lab.example.com, password: password)

### Reset Database (Fresh Start)

```bash
php artisan migrate:fresh --seed
```

---

## Testing the Installation

### 1. Health Check

```bash
curl http://localhost:8000/up
```

Expected: `{"status": "ok"}`

### 2. Login Test

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@hunting-data.example.com",
    "password": "password"
  }'
```

Expected: JSON response with user data and authentication token

### 3. Protected Endpoint Test

Use the token from login:

```bash
curl http://localhost:8000/api/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Expected: Current user information

### 4. Public Map Endpoint

```bash
curl http://localhost:8000/api/public/map/points
```

Expected: GeoJSON FeatureCollection (empty if no positive results exist)

---

## Common Issues

### Issue: Port 8000 Already in Use (Docker)

**Solution**: Change the port in `docker-compose.yml`:

```yaml
nginx:
  ports:
    - "8080:80"  # Changed from 8000 to 8080
```

Then access at http://localhost:8080

### Issue: Database Connection Failed

**Docker**: Ensure all containers are running:
```bash
docker-compose ps
```

**XAMPP**: Ensure MySQL is started in XAMPP Control Panel

Check `.env` database credentials match your setup

### Issue: Permission Denied on storage/

```bash
chmod -R 775 storage bootstrap/cache
chown -R www-data:www-data storage bootstrap/cache  # Docker
# or
chown -R daemon:daemon storage bootstrap/cache      # XAMPP Mac
# or
icacls storage /grant Users:F /T                    # XAMPP Windows
```

### Issue: Composer Install Fails

Clear Composer cache:
```bash
composer clear-cache
composer install
```

### Issue: Migration Fails with "Table already exists"

Reset migrations:
```bash
php artisan migrate:fresh --seed
```

### Issue: 404 on All Routes (XAMPP)

Ensure `mod_rewrite` is enabled in Apache and `.htaccess` exists in `public/` directory

---

## Next Steps

1. **API Documentation**: See `/docs/openapi.yaml` for complete API reference
2. **Testing**: Run feature tests with `php artisan test`
3. **Development**: Access Telescope at http://localhost:8000/telescope
4. **Production**: Follow Laravel deployment best practices

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/voineadani/quickstart-android/issues
- Documentation: `/docs/` directory

---

## License

This project is part of the quickstart-android repository.
