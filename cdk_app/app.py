#!/usr/bin/env python3
import aws_cdk as cdk

from data_stack import DataStack
from messaging_stack import MessagingStack
from compute_stack import ComputeStack

app = cdk.App()

data_stack = DataStack(app, "AwsRefresherDataStack")

messaging_stack = MessagingStack(app, "AwsRefresherMessagingStack")

compute_stack = ComputeStack(
    app,
    "AwsRefresherComputeStack",
    orders_table=data_stack.orders_table,
    order_created_topic=messaging_stack.order_created_topic,
    order_queue=messaging_stack.order_queue,
)

app.synth()
