import boto3
from decimal import Decimal
from datetime import datetime, timezone
import os
import random


dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

PRODUCTS_TABLE = os.environ.get(
    "PRODUCTS_TABLE",
    "products"
)

SUBSCRIPTIONS_TABLE = os.environ.get(
    "SUBSCRIPTIONS_TABLE",
    "subscriptions"
)

HISTORY_TABLE = os.environ.get(
    "HISTORY_TABLE",
    "price_history"
)

SNS_TOPIC_ARN = os.environ.get(
    "SNS_TOPIC_ARN"
)

products_table = dynamodb.Table(
    PRODUCTS_TABLE
)

subscriptions_table = dynamodb.Table(
    SUBSCRIPTIONS_TABLE
)

history_table = dynamodb.Table(
    HISTORY_TABLE
)


def send_price_alert(
    subscription,
    product,
    old_price,
    new_price
):

    if not SNS_TOPIC_ARN:
        print(
            "SNS_TOPIC_ARN environment variable is missing"
        )
        return

    product_name = product.get(
        "product_name",
        product["product_id"]
    )

    target_price = subscription.get(
        "target_price"
    )

    message = f"""
Scheduled Price Alert!

Product: {product_name}
Product ID: {product["product_id"]}

Previous Price: ₹{old_price}
Current Price: ₹{new_price}
Target Price: ₹{target_price}

The product has reached your target price.

Price Watch & Availability Alert System
"""

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"Price Alert: {product_name}",
        Message=message
    )

    print(
        "Price alert sent to:",
        subscription.get("user_email")
    )


def send_restock_alert(
    subscription,
    product
):

    if not SNS_TOPIC_ARN:
        print(
            "SNS_TOPIC_ARN environment variable is missing"
        )
        return

    product_name = product.get(
        "product_name",
        product["product_id"]
    )

    message = f"""
Scheduled Restock Alert!

Product: {product_name}
Product ID: {product["product_id"]}

Good news! This product is back in stock.

Current Price: ₹{product.get("current_price")}

Price Watch & Availability Alert System
"""

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"Restock Alert: {product_name}",
        Message=message
    )

    print(
        "Restock alert sent to:",
        subscription.get("user_email")
    )


def lambda_handler(event, context):

    print("Scheduled monitor started")

    products_result = products_table.scan()

    products = products_result.get(
        "Items",
        []
    )

    subscriptions_result = subscriptions_table.scan()

    subscriptions = subscriptions_result.get(
        "Items",
        []
    )

    updated_products = 0
    price_alerts = 0
    restock_alerts = 0

    # Select a subset of products for this run.
    # This keeps the simulation realistic and
    # avoids changing every product on every run.

    if len(products) > 2:
        selected_products = random.sample(
            products,
            2
        )
    else:
        selected_products = products

    for product in selected_products:

        product_id = product["product_id"]

        old_price = Decimal(
            str(product["current_price"])
        )

        old_stock = product.get(
            "in_stock",
            True
        )

        new_price = old_price
        new_stock = old_stock

        # ------------------------------------------
        # Price simulation
        # ------------------------------------------

        # 50% chance of a price change
        if random.random() < 0.50:

            # Small price movement
            if random.random() < 0.60:

                # Price drop
                new_price = (
                    old_price * Decimal("0.95")
                ).quantize(
                    Decimal("0.01")
                )

            else:

                # Small price increase
                new_price = (
                    old_price * Decimal("1.03")
                ).quantize(
                    Decimal("0.01")
                )

        # ------------------------------------------
        # Stock simulation
        # ------------------------------------------

        # Out-of-stock products have a chance
        # to become available again.
        if old_stock is False:

            if random.random() < 0.50:
                new_stock = True

        # ------------------------------------------
        # Skip if nothing changed
        # ------------------------------------------

        if (
            new_price == old_price
            and new_stock == old_stock
        ):
            continue

        now = datetime.now(
            timezone.utc
        ).isoformat()

        # ------------------------------------------
        # Update product
        # ------------------------------------------

        products_table.update_item(
            Key={
                "product_id": product_id
            },
            UpdateExpression="""
                SET previous_price = :previous_price,
                    current_price = :current_price,
                    in_stock = :in_stock,
                    last_updated = :last_updated
            """,
            ExpressionAttributeValues={
                ":previous_price": old_price,
                ":current_price": new_price,
                ":in_stock": new_stock,
                ":last_updated": now
            }
        )

        updated_products += 1

        print(
            f"Updated {product_id}: "
            f"price {old_price} -> {new_price}, "
            f"stock {old_stock} -> {new_stock}"
        )

        # ------------------------------------------
        # Price history
        # ------------------------------------------

        if new_price != old_price:

            record_id = (
                product_id
                + "-"
                + datetime.now(
                    timezone.utc
                ).strftime(
                    "%Y%m%d%H%M%S%f"
                )
            )

            history_table.put_item(
                Item={
                    "record_id": record_id,
                    "product_id": product_id,
                    "price": new_price,
                    "updated_at": now,
                    "change_type": "scheduled"
                }
            )

        # ------------------------------------------
        # Subscription checks
        # ------------------------------------------

        for subscription in subscriptions:

            if subscription.get(
                "product_id"
            ) != product_id:

                continue

            # Price alert
            if new_price != old_price:

                target_price = Decimal(
                    str(
                        subscription.get(
                            "target_price"
                        )
                    )
                )

                if new_price <= target_price:

                    try:

                        send_price_alert(
                            subscription,
                            product,
                            old_price,
                            new_price
                        )

                        price_alerts += 1

                    except Exception as e:

                        print(
                            "Price SNS error:",
                            str(e)
                        )

            # Restock alert
            if (
                old_stock is False
                and new_stock is True
                and subscription.get(
                    "notify_on_restock"
                ) is True
            ):

                try:

                    updated_product = {
                        **product,
                        "current_price": new_price
                    }

                    send_restock_alert(
                        subscription,
                        updated_product
                    )

                    restock_alerts += 1

                except Exception as e:

                    print(
                        "Restock SNS error:",
                        str(e)
                    )

    print(
        "Scheduled monitor completed"
    )

    print(
        "Products updated:",
        updated_products
    )

    print(
        "Price alerts:",
        price_alerts
    )

    print(
        "Restock alerts:",
        restock_alerts
    )

    return {
        "statusCode": 200,
        "message": "Scheduled monitoring completed",
        "products_updated": updated_products,
        "price_alerts": price_alerts,
        "restock_alerts": restock_alerts
    }