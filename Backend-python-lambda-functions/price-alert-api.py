import json
import boto3
from decimal import Decimal
from datetime import datetime, timezone
import os

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "products")
SUBSCRIPTIONS_TABLE = os.environ.get("SUBSCRIPTIONS_TABLE", "subscriptions")
HISTORY_TABLE = os.environ.get("HISTORY_TABLE", "price_history")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

products_table = dynamodb.Table(PRODUCTS_TABLE)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE)
history_table = dynamodb.Table(HISTORY_TABLE)


def decimal_to_python(value):
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict):
        return {
            key: decimal_to_python(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            decimal_to_python(item)
            for item in value
        ]

    return value


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(decimal_to_python(body))
    }


def send_price_alert(subscription, product, new_price):

    if not SNS_TOPIC_ARN:
        print("SNS_TOPIC_ARN environment variable is missing")
        return False

    email = subscription.get("user_email")
    product_name = product.get("product_name", product["product_id"])
    target_price = subscription.get("target_price")

    message = f"""
Price Alert!

Product: {product_name}
Product ID: {product["product_id"]}

Previous Price: ₹{product.get("previous_price")}
Current Price: ₹{new_price}
Your Target Price: ₹{target_price}

The product has reached your target price.

Price Watch & Availability Alert System
"""

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"Price Alert: {product_name}",
        Message=message
    )

    print(f"Price alert sent for {email}")

    return True


def lambda_handler(event, context):

    print("Received event:")
    print(json.dumps(event))

    method = event.get("requestContext", {}).get("http", {}).get("method")

    if not method:
        method = event.get("httpMethod")

    path = event.get("rawPath")

    if not path:
        path = event.get("path")

    # --------------------------------------------------
    # GET /products
    # --------------------------------------------------
    if method == "GET" and path == "/products":

        result = products_table.scan()

        products = result.get("Items", [])

        return response(
            200,
            {
                "products": products,
                "count": len(products)
            }
        )

    # --------------------------------------------------
    # GET /subscriptions
    # --------------------------------------------------
    if method == "GET" and path == "/subscriptions":

        result = subscriptions_table.scan()

        subscriptions = result.get("Items", [])

        return response(
            200,
            {
                "subscriptions": subscriptions,
                "count": len(subscriptions)
            }
        )

    # --------------------------------------------------
    # GET /price-history
    # --------------------------------------------------
    if method == "GET" and path == "/price-history":

        try:

            result = history_table.scan()

            history = result.get("Items", [])

            # Sort newest first
            history.sort(
                key=lambda item: item.get("updated_at", ""),
                reverse=True
            )

            return response(
                200,
                {
                    "price_history": history,
                    "count": len(history)
                }
            )

        except Exception as e:

            print("ERROR:", str(e))

            return response(
                500,
                {
                    "message": "Internal server error",
                    "error": str(e)
                }
            )

    # --------------------------------------------------
    # POST /subscribe
    # --------------------------------------------------
    if method == "POST" and path == "/subscribe":

        try:
            body = event.get("body")

            if isinstance(body, str):
                body = json.loads(body)

            if not body:
                return response(
                    400,
                    {
                        "message": "Request body is required"
                    }
                )

            user_email = body.get("user_email")
            product_id = body.get("product_id")
            target_price = body.get("target_price")
            notify_on_restock = body.get("notify_on_restock", False)

            if not user_email or not product_id or target_price is None:
                return response(
                    400,
                    {
                        "message": "user_email, product_id and target_price are required"
                    }
                )

            product = products_table.get_item(
                Key={
                    "product_id": product_id
                }
            )

            if "Item" not in product:
                return response(
                    404,
                    {
                        "message": "Product not found"
                    }
                )

            subscription_id = (
                user_email
                + "-"
                + product_id
                + "-"
                + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            )

            created_at = datetime.now(timezone.utc).isoformat()

            item = {
                "subscription_id": subscription_id,
                "user_email": user_email,
                "product_id": product_id,
                "target_price": Decimal(str(target_price)),
                "notify_on_restock": bool(notify_on_restock),
                "created_at": created_at
            }

            subscriptions_table.put_item(
                Item=item
            )

            return response(
                201,
                {
                    "message": "Subscription created successfully",
                    "subscription": item
                }
            )

        except Exception as e:

            print("ERROR:", str(e))

            return response(
                500,
                {
                    "message": "Internal server error",
                    "error": str(e)
                }
            )

    # --------------------------------------------------
    # POST /products/update
    # --------------------------------------------------
    if method == "POST" and path == "/products/update":

        try:
            body = event.get("body")

            if isinstance(body, str):
                body = json.loads(body)

            if not body:
                return response(
                    400,
                    {
                        "message": "Request body is required"
                    }
                )

            product_id = body.get("product_id")
            new_price = body.get("current_price")
            new_stock = body.get("in_stock")

            if not product_id:
                return response(
                    400,
                    {
                        "message": "product_id is required"
                    }
                )

            if new_price is None and new_stock is None:
                return response(
                    400,
                    {
                        "message": "current_price or in_stock is required"
                    }
                )

            result = products_table.get_item(
                Key={
                    "product_id": product_id
                }
            )

            if "Item" not in result:
                return response(
                    404,
                    {
                        "message": "Product not found"
                    }
                )

            product = result["Item"]

            old_price = product.get("current_price")

            old_stock = product.get("in_stock")

            now = datetime.now(timezone.utc).isoformat()

            update_expression = []
            expression_values = {}
            expression_names = {}

            if new_price is not None:

                update_expression.append(
                    "#current_price = :current_price"
                )

                expression_names["#current_price"] = "current_price"

                expression_values[":current_price"] = Decimal(
                    str(new_price)
                )

                if old_price is not None:

                    update_expression.append(
                        "#previous_price = :previous_price"
                    )

                    expression_names["#previous_price"] = "previous_price"

                    expression_values[":previous_price"] = Decimal(
                        str(old_price)
                    )

            if new_stock is not None:

                update_expression.append(
                    "#in_stock = :in_stock"
                )

                expression_names["#in_stock"] = "in_stock"

                expression_values[":in_stock"] = bool(new_stock)

            update_expression.append(
                "#last_updated = :last_updated"
            )

            expression_names["#last_updated"] = "last_updated"

            expression_values[":last_updated"] = now

            restock_detected = (
               old_stock is False
               and new_stock is True
            )

            update_result = products_table.update_item(
                Key={
                    "product_id": product_id
                },
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW"
            )

            updated_product = update_result["Attributes"]

                        # --------------------------------------------------
            # Check for restock notifications
            # --------------------------------------------------

            alerts_sent = 0

            if restock_detected:

                subscription_result = subscriptions_table.scan()

                subscriptions = subscription_result.get(
                    "Items",
                    []
                )

                for subscription in subscriptions:

                    if subscription.get("product_id") != product_id:
                        continue

                    if subscription.get("notify_on_restock") is not True:
                        continue

                    try:

                        send_restock_alert(
                            subscription,
                            updated_product
                        )

                        alerts_sent += 1

                    except Exception as sns_error:

                        print(
                            "SNS RESTOCK ERROR:",
                            str(sns_error)
                        )

            if new_price is not None:

                record_id = (
                    product_id
                    + "-"
                    + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
                )

                history_table.put_item(
                    Item={
                        "record_id": record_id,
                        "product_id": product_id,
                        "price": Decimal(str(new_price)),
                        "updated_at": now,
                        "change_type": "manual"
                    }
                )

            return response(
                200,
                {
                    "message": "Product updated successfully",
                    "product": updated_product,
                     "restock_detected": restock_detected,
                     "alerts_sent": alerts_sent
                }
            )

        except Exception as e:

            print("ERROR:", str(e))

            return response(
                500,
                {
                    "message": "Internal server error",
                    "error": str(e)
                }
            )

    # --------------------------------------------------
    # POST /simulate-drop
    # --------------------------------------------------
    if method == "POST" and path == "/simulate-drop":

        try:

            body = event.get("body")

            if isinstance(body, str):
                body = json.loads(body)

            product_id = body.get("product_id")

            if not product_id:
                return response(
                    400,
                    {
                        "message": "product_id is required"
                    }
                )

            result = products_table.get_item(
                Key={
                    "product_id": product_id
                }
            )

            if "Item" not in result:
                return response(
                    404,
                    {
                        "message": "Product not found"
                    }
                )

            product = result["Item"]

            current_price = Decimal(
                str(product["current_price"])
            )

            new_price = (
                current_price * Decimal("0.90")
            ).quantize(
                Decimal("0.01")
            )

            now = datetime.now(timezone.utc).isoformat()

            products_table.update_item(
                Key={
                    "product_id": product_id
                },
                UpdateExpression="""
                    SET previous_price = :previous_price,
                        current_price = :current_price,
                        last_updated = :last_updated
                """,
                ExpressionAttributeValues={
                    ":previous_price": current_price,
                    ":current_price": new_price,
                    ":last_updated": now
                }
            )

            record_id = (
                product_id
                + "-"
                + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            )

            history_table.put_item(
                Item={
                    "record_id": record_id,
                    "product_id": product_id,
                    "price": new_price,
                    "updated_at": now,
                    "change_type": "simulated"
                }
            )

            # --------------------------------------------------
            # Check subscriptions and send alerts
            # --------------------------------------------------

            subscription_result = subscriptions_table.scan()

            subscriptions = subscription_result.get(
                "Items",
                []
            )

            alerts_sent = 0

            for subscription in subscriptions:

                if subscription.get("product_id") != product_id:
                    continue

                target_price = Decimal(
                    str(subscription.get("target_price"))
                )

                if new_price <= target_price:

                    try:

                        send_price_alert(
                            subscription,
                            {
                                **product,
                                "previous_price": current_price
                            },
                            new_price
                        )

                        alerts_sent += 1

                    except Exception as sns_error:

                        print(
                            "SNS ERROR:",
                            str(sns_error)
                        )

            return response(
                200,
                {
                    "message": "Price drop simulated successfully",
                    "product_id": product_id,
                    "previous_price": current_price,
                    "new_price": new_price,
                    "alerts_sent": alerts_sent
                }
            )

        except Exception as e:

            print("ERROR:", str(e))

            return response(
                500,
                {
                    "message": "Internal server error",
                    "error": str(e)
                }
            )

    # --------------------------------------------------
    # Route not found
    # --------------------------------------------------
    return response(
        404,
        {
            "message": "Route not found",
            "method": method,
            "path": path
        }
    )