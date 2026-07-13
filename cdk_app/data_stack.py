from aws_cdk import Stack, RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class DataStack(Stack):
    """
    Part A: DynamoDB Orders table.

    Note: Aurora is provisioned separately via the AWS CLI using the new
    "express configuration" flow (GA March 2026), not through this CDK
    stack - CDK/CloudFormation doesn't yet support the
    WithExpressConfiguration parameter that Free Plan accounts require.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.orders_table = dynamodb.Table(
            self,
            "OrdersTable",
            table_name="Orders",
            partition_key=dynamodb.Attribute(
                name="orderId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )