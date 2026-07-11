from aws_cdk import Stack, RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class DataStack(Stack):
    """
    Part A: DynamoDB Orders table.
    Part B will add an Aurora Serverless v2 cluster to this stack.
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
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # on-demand, free-tier friendly
            removal_policy=RemovalPolicy.DESTROY,  # fine for a throwaway interview-prep project
        )
