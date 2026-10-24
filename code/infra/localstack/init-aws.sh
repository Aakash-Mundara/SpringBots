#!/bin/bash
# LocalStack ready-hook: creates the private document bucket, the DLQ and the main extraction
# queue with a redrive policy (maxReceiveCount 3) and a 120 s visibility timeout (Section 2.2).
set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-ap-south-1}"
BUCKET="${S3_BUCKET:-onboardiq-docs}"
QUEUE="${SQS_QUEUE:-onboardiq-extraction}"
DLQ="${SQS_DLQ:-onboardiq-extraction-dlq}"

echo "[init-aws] creating bucket ${BUCKET}"
awslocal s3api create-bucket --bucket "${BUCKET}" --region "${REGION}" \
  --create-bucket-configuration LocationConstraint="${REGION}" >/dev/null 2>&1 || true
awslocal s3api put-public-access-block --bucket "${BUCKET}" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "[init-aws] creating DLQ ${DLQ}"
DLQ_URL=$(awslocal sqs create-queue --queue-name "${DLQ}" \
  --attributes MessageRetentionPeriod=1209600 --query QueueUrl --output text)
DLQ_ARN=$(awslocal sqs get-queue-attributes --queue-url "${DLQ_URL}" \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)

echo "[init-aws] creating queue ${QUEUE} -> redrive to ${DLQ_ARN}"
cat > /tmp/queue-attrs.json <<EOF
{
  "VisibilityTimeout": "120",
  "ReceiveMessageWaitTimeSeconds": "20",
  "RedrivePolicy": "{\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"3\"}"
}
EOF
awslocal sqs create-queue --queue-name "${QUEUE}" --attributes file:///tmp/queue-attrs.json >/dev/null

touch /tmp/onboardiq-ready
echo "[init-aws] done"
