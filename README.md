# AWS Hands-On Refresher — Digital Dreamworks Interview Prep

Weekend refresher project: event-driven order pipeline (DynamoDB) migrating to
Aurora PostgreSQL, all as CDK. See project knowledge doc for full design/rationale.

## Status
- [x] Part A — Core event-driven flow (DynamoDB, Lambda x2, API Gateway, SNS, SQS, S3) — **scaffolded, ready to deploy**
- [ ] Part B — Aurora migration + contract test
- [ ] Part C — EC2 / Elastic Beanstalk / raw CloudFormation
- [ ] Part D — already true by construction (everything is CDK stacks)

## Cost — Part A only
Everything in Part A is free-tier eligible at this usage level (a handful of test
requests): DynamoDB on-demand, Lambda, API Gateway, SNS, SQS, S3. **No hourly cost
while idle.** Nothing here needs proactive teardown for cost reasons — but `cdk destroy`
is still good hygiene when you're done, since it also cleans up the S3 bucket/log
groups CDK created.

⚠️ Aurora (Part B) is NOT free-tier eligible — even at minimum 0.5 ACU it bills
per hour while the cluster exists, roughly $0.06–0.09/hr depending on region, plus
storage. I'll flag the exact estimate again right before we deploy it, and will remind
you to `cdk destroy` it before you close out any session where it's running.

## Setup

```bash
cd cdk_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# one-time per AWS account/region
cdk bootstrap
```

## Deploy Part A

```bash
cd cdk_app
cdk deploy AwsRefresherDataStack AwsRefresherMessagingStack AwsRefresherComputeStack
```

CDK will print the API Gateway URL as a stack output once deployed (add
`CfnOutput` if you want it printed explicitly — see note below).

## Test it

```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/order \
  -H "Content-Type: application/json" \
  -d '{"customerName": "Nalinka Test", "item": "Widget", "amount": 42.50}'
```

Then check:
- DynamoDB console → `Orders` table → item written
- S3 console → `order-receipts-bucket...` → `receipts/<orderId>.json` written
  (may take a few seconds — SNS → SQS → Lambda is async)
- CloudWatch Logs for both Lambdas, to see the flow end-to-end

Try posting with `"amount": -5` to see the ProcessOrder Lambda deliberately fail
and the message land in the DLQ after 3 retries — good live demo of at-least-once
delivery + idempotency talking points.

## Teardown

```bash
cd cdk_app
cdk destroy --all
```

Run this at the end of any work session. For Part A there's no cost risk left running,
but destroying keeps your account tidy and avoids any surprise with S3/log retention.
**Once Aurora (Part B) is deployed, this step is no longer optional** — see the cost
note above.

## Talking points — Part A
*"I rebuilt a small event-driven order pipeline this weekend — API Gateway into a
Lambda that writes to DynamoDB and publishes to SNS, fanning out through SQS to a
second Lambda that validates and writes a receipt to S3. It's a good sandbox for
talking about async decoupling, at-least-once delivery, and scoping IAM roles per
Lambda rather than sharing one broad role."*
