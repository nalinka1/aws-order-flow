from aws_cdk import Stack, Duration
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct


class MessagingStack(Stack):
    """
    Part A: SNS topic (OrderCreatedTopic) fanning out to an SQS queue
    (OrderQueue), with a dead-letter queue for messages that repeatedly
    fail processing (e.g. invalid amount) — good talking point on
    at-least-once delivery / idempotency.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.order_created_topic = sns.Topic(
            self, "OrderCreatedTopic", topic_name="OrderCreatedTopic"
        )

        self.dead_letter_queue = sqs.Queue(
            self,
            "OrderQueueDLQ",
            queue_name="OrderQueueDLQ",
            retention_period=Duration.days(2),
        )

        self.order_queue = sqs.Queue(
            self,
            "OrderQueue",
            queue_name="OrderQueue",
            visibility_timeout=Duration.seconds(30),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3, queue=self.dead_letter_queue
            ),
        )

        self.order_created_topic.add_subscription(
            subs.SqsSubscription(self.order_queue)
        )
