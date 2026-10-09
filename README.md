Manufacturing Production and Quality Control Management System

Project Overview

The Manufacturing Production and Quality Control Management System is a backend application developed using FastAPI and Python. It manages manufacturing plants, production lines, products, raw materials, bills of materials, machines, production orders, production batches, workers, shifts, quality inspections, defects, maintenance, downtime, inventory movements, approval workflows, dashboards, reports, audit logs, and notifications.

The system provides role-based access control, JWT authentication, inventory validation, production workflow management, quality tracking, and audit logging.

Technology Stack

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* SQLite for local development
* JWT authentication
* Alembic for database migrations
* Pytest for testing
* Uvicorn for running the application
* Docker for containerization

Project Features

1. Authentication and Role-Based Access Control

* User registration and login
* JWT access tokens
* Refresh token management
* User profile retrieval
* Logout and token revocation
* User activation and deactivation
* Role-based access control

Supported roles include Super Admin, Plant Manager, Production Manager, Quality Manager, Maintenance Engineer, Store Manager, Production Supervisor, and Worker.

2. Plant Management

* Create, retrieve, update, and manage manufacturing plants
* Manage plant information
* Support plant status and lifecycle management

3. Production Line Management

* Create and manage production lines
* Associate production lines with manufacturing plants
* Retrieve and update production line information

4. Product Management

* Create and manage products
* Maintain product information
* Retrieve and update product records

5. Raw Material Management

* Manage raw materials
* Track available stock
* Record stock-in and stock-out operations
* Adjust inventory quantities
* View inventory history
* Prevent negative inventory balances

6. Bill of Materials Management

* Create bills of materials
* Associate raw materials with products
* Retrieve BOM details
* Update and deactivate BOM records
* Calculate material requirements

7. Machine Management

* Register and manage machines
* Update machine status
* Check machine availability
* Prevent unavailable machines from being assigned to production

8. Production Order Management

* Create and manage production orders
* Track production order status
* Check material availability
* Manage production order lifecycle transitions

9. Production Batch Management

* Create and retrieve production batches
* Start production batches
* Record production output
* Track rejected quantities
* Complete or reject batches according to business rules

10. Worker Management

* Create and manage worker records
* Update worker status
* Assign and unassign workers to production batches
* Retrieve batch worker assignments

11. Shift Management

* Create and manage production shifts
* Update shift information
* Manage shift status

12. Quality Inspection

* Record quality inspections
* Track inspected, passed, and failed quantities
* Retrieve inspection records
* Associate inspections with production batches

13. Defect Management

* Record manufacturing defects
* Track defect quantities and severity
* Retrieve and update defect records
* Support critical-defect notification workflows

14. Maintenance Management

* Create and manage maintenance records
* Track maintenance status
* Retrieve maintenance information

15. Downtime Management

* Record machine downtime
* Track downtime duration
* Update and close downtime records
* Generate downtime reports

16. Inventory Movement Management

* Record inventory movements
* Track stock-in and stock-out quantities
* Record inventory adjustments
* Maintain inventory movement history

17. Production Approval Workflow

* Submit production approval requests
* Retrieve approval records
* Approve or reject requests
* Apply production order status transitions according to the workflow

18. Dashboard

* Retrieve manufacturing summary statistics
* View counts of plants, production lines, products, orders, batches, machines, workers, materials, inspections, defects, maintenance records, downtime records, and inventory movements

19. Advanced Reports

* Production reports
* Quality reports
* Inventory reports
* Downtime reports
* Maintenance reports

20. Audit Logs

* Retrieve audit logs
* Retrieve an individual audit record
* Retrieve audit logs associated with a user
* Restrict audit log access to authorized Super Admin users
* Track selected manufacturing and production operations

21. Notifications

* Retrieve notifications
* Mark individual notifications as read
* Mark all notifications as read
* Notify relevant users about critical defects

22. Security and Performance

* JWT-based authentication
* Role-based authorization
* Login failure rate limiting
* Security response headers
* CORS configuration
* Refresh token revocation
* Paginated listing support where implemented

23. Testing and Deployment

* Automated integration tests
* Pytest-based testing
* Alembic migration support
* Docker configuration for deployment

Project Structure

app/
api/
auth/
plants/
production_lines/
products/
materials/
bom/
machines/
production_orders/
batches/
workers/
shifts/
quality/
defects/
maintenance/
downtime/
inventory/
approvals/
dashboard/
reports/
audit/
notifications/
models/
schemas/
services/
repositories/
core/
db/
middleware/
utils/

tests/
unit/
integration/

postman/

alembic/

.env.example
.gitignore
alembic.ini
Dockerfile
docker-compose.yml
requirements.txt
README.md

Prerequisites

* Python 3.11 or later
* pip
* Git
* Docker Desktop if running the containerized application

The project has been tested in a local environment using SQLite. Other database engines require the appropriate configuration and dependencies.

Installation

1. Open PowerShell and navigate to the project directory.

2. Create a virtual environment.

   python -m venv venv

3. Activate the virtual environment.

   .\venv\Scripts\Activate.ps1

4. Install the project dependencies.

   pip install -r requirements.txt

Environment Configuration

Create a .env file in the project root directory. Use .env.example as a reference.

Example development configuration:

DATABASE_URL=sqlite:///./manufacturing.db
SECRET_KEY=replace-with-a-strong-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

Use a strong secret key in non-development environments. Do not commit the .env file or production secrets to version control.

Database Migrations

The project uses Alembic to manage database schema migrations.

Check the current database revision:

```
alembic current
```

View available migration heads:

```
alembic heads
```

Apply migrations:

```
alembic upgrade head
```

Generate a migration after changing SQLAlchemy models:

```
alembic revision --autogenerate -m "describe schema change"
```

Review autogenerated migrations before applying them. Back up important databases before performing schema changes.

Application Startup

Start the FastAPI application from the project root:

```
uvicorn app.main:app --reload
```

The local development server runs at:

```
http://127.0.0.1:8000
```

Swagger API documentation:

```
http://127.0.0.1:8000/docs
```

ReDoc documentation:

```
http://127.0.0.1:8000/redoc
```

Authentication

Register a user through the registration endpoint:

```
POST /auth/register
```

Log in:

```
POST /auth/login
```

Refresh an access token:

```
POST /auth/refresh
```

Retrieve the current user:

```
GET /auth/me
```

Log out:

```
POST /auth/logout
```

Use the access token in the Authorization header for protected endpoints:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

The actual permissions available to each role are determined by the application's authorization rules.

Testing

Run the complete integration test suite:

```
pytest tests/integration/ -v
```

Run a specific test file:

```
pytest tests/integration/test_audit.py -v
```

Run the entire test suite, including unit tests if present:

```
pytest -v
```

The integration suite has previously completed with 252 passed tests and no reported failures. Test results may vary after code or environment changes.

Docker

If Docker Desktop and the required virtualization components are available, build and start the application using:

```
docker compose up --build
```

Stop the containers using:

```
docker compose down
```

Review the Dockerfile, docker-compose.yml, database configuration, and environment variables before deployment. The application must be configured so that its database and other required resources are available inside the container.

API Testing with Postman

The project includes a postman directory for API testing resources.

Import the available Postman collection into Postman. Configure the base URL as:

```
http://127.0.0.1:8000
```

Run authentication requests first and use the returned access token for protected endpoints.

Business Rules

* Inventory quantities must not become negative.
* Protected endpoints require appropriate authentication and authorization.
* Production order status transitions must follow the implemented workflow.
* Material availability must be checked before production starts.
* Quality inspections are required by the relevant batch completion workflow.
* Unavailable machines must not be assigned to production.
* Critical defects trigger notifications for designated roles.
* Audit logs provide a record of selected operations.
* Inventory and production operations must preserve data consistency.

Security Considerations

* Store secrets in environment variables.
* Do not commit credentials or production database files.
* Use HTTPS in production.
* Configure production CORS origins explicitly.
* Apply appropriate database access controls.
* Review authentication, authorization, rate limiting, and audit logging before deployment.
* Back up the database regularly.

Future Improvements

* Add broader automated unit and end-to-end tests.
* Review and reduce deprecated API usage and test warnings.
* Add production-grade database configuration.
* Improve monitoring, structured logging, and operational metrics.
* Configure a production-ready deployment pipeline.

Author

Manufacturing Production and Quality Control Management System

Project Status

The application includes implementations for the 23 planned development levels. The integration test suite has previously passed 252 tests. Final deployment configuration, migration validation, documentation, and submission artifacts should be verified before production use.
