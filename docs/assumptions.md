# Assumptions Documentation

This document lists the assumptions made during the development of the Hunting Data System.

## Database & Infrastructure

1. **MySQL Version**: Using MySQL 8.0 or higher with spatial data support (POINT geometry type)
2. **PHP Version**: Using PHP 8.3.6 (compatible with Laravel 11)
3. **Database Connection**: Default connection name is `mysql` in Laravel
4. **Storage**: Using local filesystem for file storage (can be extended to S3 later)
5. **Cache**: Using file-based cache (can be upgraded to Redis in production)

## User Roles & Permissions

1. **Role Structure**: Three primary roles - HUNTER, LAB, and ADMIN
2. **Role Hierarchy**: 
   - HUNTER: Can create protocols, view their own protocols and results
   - LAB: Can view assigned protocols, enter test results for Trichinella and ASF
   - ADMIN: Full access to all resources, can manage users, labs, and assign protocols
3. **Default User**: System creates an admin user during seeding
4. **Lab Assignment**: Users with LAB role must be assigned to a lab (lab_id required)

## Protocol & Sample Management

1. **Sample Barcode**: Unique identifier for samples, assumed to be alphanumeric string
2. **Game Species**: Free text field (could be enum in future iterations)
3. **Animal Sex**: Stored as string (M/F/Unknown)
4. **Animal Age**: Stored as integer (months) or string description
5. **Animal Weight**: Stored in kilograms as decimal
6. **Sample Types**: Free text field (e.g., "muscle", "blood", "tissue")
7. **Category**: Free text field for hunting category/license type

## Test Results

1. **Result States**: Three states - `positive`, `negative`, `pending`
2. **Initial State**: New protocols have no results (NULL), labs set them to positive/negative
3. **Timestamp Recording**: Automatically recorded when lab enters results
4. **Result Immutability**: Results can be updated but changes are logged via activity log
5. **Authorized Tests**: Labs must be authorized (flag) to perform specific tests (Trichinella/ASF)

## Geographic Data

1. **GPS Coordinates**: Using decimal degrees (WGS84 coordinate system)
2. **GPS Precision**: Standard mobile GPS precision (~5-10 meters)
3. **Admin Address**: String field for administrative location (city, region, country)
4. **Spatial Index**: Created on POINT geometry for efficient spatial queries
5. **Public Map**: Only shows confirmed positive results to protect hunter privacy

## API & Authentication

1. **API Format**: RESTful JSON API
2. **Authentication**: Token-based using Laravel Sanctum (Bearer tokens)
3. **Token Expiration**: Tokens do not expire by default (can be configured)
4. **API Versioning**: Not implemented initially (can add v1/ prefix if needed)
5. **Rate Limiting**: Using Laravel default (60 requests per minute per user)

## Public Map

1. **Data Privacy**: Only displays lat/lon and disease flags (no hunter info, no exact location details)
2. **Cache Duration**: 15 minutes for map data
3. **Bbox Parameter**: Expected format: `min_lon,min_lat,max_lon,max_lat`
4. **GeoJSON Output**: Standard GeoJSON FeatureCollection format
5. **Disease Filter**: Multiple diseases can be filtered with comma separation

## Testing & Quality

1. **Test Framework**: Using Pest PHP for feature tests
2. **Test Database**: Using SQLite in-memory for testing
3. **Factory Data**: Faker library for generating realistic test data
4. **Code Style**: Laravel Pint for code formatting
5. **Static Analysis**: PHPStan at level 5 (can increase gradually)

## Docker & Deployment

1. **Container Setup**: PHP 8.2+, MySQL 8, Nginx
2. **Development Environment**: Docker Compose for local development
3. **Alternative Setup**: XAMPP with Apache also supported
4. **Public Directory**: Laravel public folder must be web root
5. **Environment Variables**: All config via .env file (never committed)

## Activity Logging

1. **Log All CRUD**: All create, update, delete operations are logged
2. **Log Retention**: No automatic cleanup (can add scheduled task later)
3. **Log Detail**: Includes user, action, old/new values, timestamp
4. **Performance**: Async logging could be added for high-volume scenarios

## Future Considerations

1. **Notifications**: Email/SMS notifications for critical results not implemented yet
2. **Multi-language**: System assumes English, i18n can be added
3. **Mobile App**: API designed to support future Capacitor + React app
4. **File Uploads**: Photo upload for samples not implemented in phase 1
5. **Reporting**: Advanced analytics and PDF reports planned for phase 2
6. **Audit Trail**: More detailed audit trail with IP tracking could be added
7. **Two-Factor Auth**: 2FA not implemented but Sanctum supports it

## Data Validation

1. **Phone Numbers**: Stored as string, basic format validation
2. **Email**: Laravel validation rules for email format
3. **Barcodes**: Alphanumeric, unique across system
4. **GPS Coordinates**: Valid lat/lon ranges (-90 to 90, -180 to 180)
5. **Required Fields**: Minimum required fields to create protocol

## Performance

1. **Pagination**: Default 15 items per page for lists
2. **Database Indexes**: On frequently queried columns (barcode, lab_id, created_at)
3. **Eager Loading**: Used to prevent N+1 queries
4. **Query Optimization**: Spatial queries optimized with SPATIAL INDEX
5. **Caching Strategy**: Cache expensive queries (public map, statistics)
