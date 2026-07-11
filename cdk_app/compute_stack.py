from aws_cdk import Stack, Duration, RemovalPolicy
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct


class ComputeStack(Stack):
    """
    Part A: CreateOrderFunction (API GW -> Lambda -> DynamoDB + SNS publish)
    and ProcessOrderFunction (SQS -> Lambda -> S3).
    IAM: each Lambda gets only the grants it needs (least privilege).
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        orders_table: dynamodb.Table,
        order_created_topic: sns.Topic,
        order_queue: sqs.Queue,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.receipts_bucket = s3.Bucket(
            self,
            "OrderReceiptsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # convenient for repeated deploy/destroy cycles
        )

        create_order_fn = _lambda.Function(
            self,
            "CreateOrderFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/create_order"),
            timeout=Duration.seconds(10),
            environment={
                "ORDERS_TABLE_NAME": orders_table.table_name,
                "ORDER_CREATED_TOPIC_ARN": order_created_topic.topic_arn,
            },
        )
        orders_table.grant_write_data(create_order_fn)
        order_created_topic.grant_publish(create_order_fn)

        process_order_fn = _lambda.Function(
            self,
            "ProcessOrderFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/process_order"),
            timeout=Duration.seconds(10),
            environment={
                "RECEIPTS_BUCKET_NAME": self.receipts_bucket.bucket_name,
            },
        )
        self.receipts_bucket.grant_put(process_order_fn)
        process_order_fn.add_event_source(
            SqsEventSource(order_queue, batch_size=5, report_batch_item_failures=True)
        )

        api = apigw.RestApi(
            self,
            "OrdersApi",
            rest_api_name="Orders Service",
            deploy_options=apigw.StageOptions(stage_name="prod"),
        )
        order_resource = api.root.add_resource("order")
        order_resource.add_method(
            "POST", apigw.LambdaIntegration(create_order_fn)
        )

        self.api = api
        self.create_order_fn = create_order_fn
        self.process_order_fn = process_order_fn
