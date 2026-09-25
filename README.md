
````markdown
# AWS Product Price Watch & Availability Alert System

An AWS serverless application that monitors product prices and availability, stores tracking data, and sends alerts when a product becomes available or its price changes.

## 1. Project Overview

This project demonstrates how to build a complete serverless price monitoring and alert system using AWS services.

The system allows users to:

- Add products for monitoring
- Store product and tracking information
- Check product price and availability
- Detect price/availability changes
- Trigger notifications when conditions are met
- Access the system through REST APIs
- Use CORS-enabled endpoints from a frontend application

The project is designed using AWS managed services so that there is no traditional backend server to maintain.

---

## 2. Architecture

The application follows a serverless architecture:

```text
Client / Browser
       |
       v
API Gateway
       |
       v
AWS Lambda
       |
       +------------------+
       |                  |
       v                  v
   DynamoDB           Notification
                         Service
                           |
                           v
                         Email
````

Scheduled monitoring can be connected through:

```text
EventBridge Scheduler
        |
        v
     Lambda
        |
        v
 Product Check
        |
        v
   DynamoDB
        |
        v
 Notification
```

---

## 3. AWS Services Used

### Amazon API Gateway

Provides REST API endpoints for the application.

### AWS Lambda

Contains the application/business logic without requiring a dedicated server.

### Amazon DynamoDB

Stores product information, prices, availability status, and tracking data.

### Amazon EventBridge

Can trigger scheduled product monitoring automatically.

### Amazon SES

Used for sending email notifications when configured.

### AWS IAM

Controls permissions between AWS services.

---

## 4. Main Features

* Serverless backend
* REST API
* Product tracking
* Price monitoring
* Availability monitoring
* DynamoDB persistence
* Scheduled monitoring support
* Email alert support
* CORS support
* Error handling
* JSON API responses
* AWS IAM-based permissions

---

## 5. Prerequisites

Before deploying or testing the project, make sure you have:

* AWS account
* AWS Console access
* IAM permissions for the required services
* API Gateway
* Lambda
* DynamoDB
* EventBridge
* SES (if email alerts are enabled)
* A verified email address for SES testing
* Internet access for product data retrieval

Optional:

* AWS CLI
* Postman
* Browser
* Git

---

## 6. Project Setup

### Step 1 - Create DynamoDB Table

Create the DynamoDB table used by the application.

Configure the table according to the partition key defined in the Lambda code.

Example:

```text
Table Name:
ProductPriceWatch
```

Make sure the Lambda execution role has permission to read and write to the table.

---

### Step 2 - Create Lambda Function

Create the Lambda function containing the backend logic.

Configure:

```text
Runtime:
Python

Handler:
lambda_function.lambda_handler
```

Upload the project source code and required dependencies.

Set the required environment variables.

Example:

```text
TABLE_NAME=ProductPriceWatch
```

Add additional variables required by the notification configuration.

---

### Step 3 - Configure IAM Role

The Lambda execution role should have only the permissions required by the application.

Typical permissions include:

```text
DynamoDB:
GetItem
PutItem
UpdateItem
Scan
Query

SES:
SendEmail
SendRawEmail

CloudWatch:
CreateLogGroup
CreateLogStream
PutLogEvents
```

Avoid granting unnecessary administrator permissions.

---

## 7. API Gateway Setup

Create an API Gateway REST API and connect it to the Lambda function.

Example endpoints:

```text
POST   /products
GET    /products
GET    /products/{id}
PUT    /products/{id}
DELETE /products/{id}
```

Use the exact routes configured in your deployed API.

Enable:

```text
CORS
```

for browser-based clients.

Deploy the API to a stage such as:

```text
prod
```

The resulting API URL will look like:

```text
https://<api-id>.execute-api.<region>.amazonaws.com/prod
```

---

## 8. Product Creation

A product can be added using a POST request.

Example:

```json
{
  "name": "Example Product",
  "url": "https://example.com/product",
  "target_price": 5000,
  "email": "user@example.com"
}
```

The Lambda function validates the request and stores the product information in DynamoDB.

---

## 9. Product Monitoring

The monitoring process performs the following operations:

```text
1. Read tracked products
2. Access product information
3. Extract current price
4. Check availability
5. Compare with stored values
6. Update DynamoDB
7. Trigger notification when required
```

The stored state allows the application to determine whether a product has changed.

---

## 10. Price Change Detection

The system compares the current product price with the previously stored price.

Example:

```text
Previous Price: ₹6,000
Current Price:  ₹5,000
```

The system detects:

```text
Price Changed: YES
```

The latest value is then stored in DynamoDB.

---

## 11. Availability Detection

The application also checks whether the product is available.

Example:

```text
Previous Status:
OUT_OF_STOCK

Current Status:
IN_STOCK
```

This represents an availability change.

If notification rules are satisfied, an alert is generated.

---

## 12. Notifications

When a configured monitoring condition is satisfied, the application can send an email notification.

Example notification:

```text
Product Alert

Product:
Example Product

Previous Price:
₹6,000

Current Price:
₹5,000

Availability:
IN STOCK

Status:
Price changed / Product available
```

SES must be configured and verified before production email delivery.

---

## 13. Scheduled Monitoring

EventBridge can invoke the monitoring Lambda function at a fixed interval.

Example:

```text
Every 15 minutes
Every 30 minutes
Every 1 hour
```

The flow becomes:

```text
EventBridge
    |
    v
Lambda
    |
    v
Read DynamoDB
    |
    v
Check Products
    |
    v
Update Status
    |
    v
Send Alert
```

---

## 14. CORS

CORS is enabled so that the API can be accessed from browser-based applications.

Typical configuration allows:

```text
Access-Control-Allow-Origin
Access-Control-Allow-Methods
Access-Control-Allow-Headers
```

For production, restrict the allowed origin instead of using a wildcard when appropriate.

---

## 15. API Testing

The API can be tested using:

* Browser
* Postman
* curl
* Frontend application
* AWS API Gateway testing tools

Example:

```bash
curl https://<api-id>.execute-api.<region>.amazonaws.com/prod/products
```

Expected response:

```json
{
  "products": []
}
```

or a JSON array/object containing tracked products.

---

## 16. Successful Product Creation

A successful POST request should return a JSON response indicating that the product was created.

Example:

```json
{
  "message": "Product added successfully",
  "product_id": "..."
}
```

The exact response depends on the deployed Lambda implementation.

---

## 17. Successful Product Retrieval

A GET request should return stored product information.

Example:

```json
{
  "id": "123",
  "name": "Example Product",
  "url": "https://example.com/product",
  "price": 5000,
  "availability": "IN_STOCK"
}
```

---

## 18. DynamoDB Verification

After adding a product, open:

```text
AWS Console
→ DynamoDB
→ Tables
→ ProductPriceWatch
→ Explore table items
```

You should see the stored product record.

Verify that:

* Product ID exists
* Product name is stored
* Product URL is stored
* Price is stored
* Availability is stored
* Tracking information is present

---

## 19. Lambda Logs

For debugging, use:

```text
AWS Console
→ Lambda
→ Function
→ Monitor
→ View CloudWatch logs
```

Logs should help identify:

* Request processing
* Product extraction
* Price comparison
* Availability detection
* DynamoDB operations
* Notification attempts
* Errors

Do not log sensitive credentials or private information.

---

## 20. Expected End-to-End Flow

A complete successful workflow looks like this:

```text
User
 ↓
API Gateway
 ↓
Lambda
 ↓
Validate Request
 ↓
DynamoDB
 ↓
Product Stored
 ↓
EventBridge Trigger
 ↓
Monitoring Lambda
 ↓
Check Product
 ↓
Compare Price/Availability
 ↓
Update DynamoDB
 ↓
Send Notification
```

---

## 21. Error Handling

The API should return appropriate HTTP status codes.

Typical examples:

```text
200 OK
201 Created
400 Bad Request
404 Not Found
500 Internal Server Error
```

Invalid requests should return a meaningful JSON error message instead of exposing internal implementation details.

---

## 22. Security Considerations

Follow AWS least-privilege principles.

Recommended practices:

* Use IAM roles instead of hard-coded credentials
* Keep secrets outside source code
* Restrict DynamoDB permissions
* Restrict SES permissions
* Enable API authentication for production use
* Restrict CORS origins
* Monitor CloudWatch logs
* Never commit AWS credentials to Git

---

## 23. Project Design Principles

The system is designed around:

* Serverless architecture
* Loose coupling
* Managed AWS services
* Event-driven processing
* Persistent state using DynamoDB
* Automated monitoring
* API-based access
* Minimal infrastructure management

This allows the system to scale without maintaining traditional application servers.

---

## 24. Testing Checklist

Before considering the deployment complete, verify:

```text
[✓] DynamoDB table created
[✓] Lambda deployed
[✓] IAM permissions configured
[✓] API Gateway connected
[✓] API deployed
[✓] CORS enabled
[✓] POST endpoint tested
[✓] GET endpoint tested
[✓] DynamoDB data verified
[✓] Monitoring tested
[✓] Price change tested
[✓] Availability change tested
[✓] Notification tested
[✓] CloudWatch logs verified
```

---

## 25. Expected Final Result

After successful deployment, the application provides a complete AWS-based product monitoring system.

Users can register products through the API, while AWS services handle storage, monitoring, processing, and notifications.

The final system operates without requiring a continuously running backend server.

---

## 26. Future Improvements

Possible improvements include:

* Frontend dashboard
* User authentication
* Multiple notification channels
* SMS notifications using SNS
* More product websites
* Price history charts
* User-specific product lists
* Advanced alert rules
* CloudWatch alarms
* Infrastructure as Code using AWS SAM/CDK
* CI/CD deployment pipeline
* Automated unit and integration testing

---

## 27. Conclusion

This project demonstrates a practical serverless architecture using AWS.

The combination of:

```text
API Gateway
Lambda
DynamoDB
EventBridge
SES
IAM
CloudWatch
```

creates a complete foundation for an automated product price and availability monitoring platform.

The project is suitable for learning AWS serverless architecture, REST API development, event-driven processing, database integration, and automated notifications.

```

This version is **under 200 lines** and is structured so you can place it directly in the project's `README.md`.
```
