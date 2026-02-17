#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load config from samconfig.toml
REGION=$(grep 'region = ' "$PROJECT_ROOT/infrastructure/samconfig.toml" | cut -d'"' -f2)
STACK_NAME=$(grep 'stack_name = ' "$PROJECT_ROOT/infrastructure/samconfig.toml" | cut -d'"' -f2)

echo "Deleting Video Summarization stack..."
echo "Stack:  $STACK_NAME"
echo "Region: $REGION"
echo "=========================================="
echo ""
echo "WARNING: This will permanently delete all resources including:"
echo "  - S3 buckets and all stored videos/audio/transcripts"
echo "  - Lambda functions"
echo "  - DynamoDB tables"
echo "  - Cognito user pool"
echo "  - CloudFront distribution"
echo "  - All other stack resources"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Deletion cancelled."
    exit 0
fi

echo ""
echo "Starting deletion..."

# Function to empty an S3 bucket (including versioned objects)
empty_bucket() {
    local bucket=$1
    echo "Emptying bucket: $bucket"

    # Delete all object versions
    aws s3api list-object-versions --bucket "$bucket" --region "$REGION" --output json 2>/dev/null | \
    jq -r '.Versions[]? | "\(.Key)\t\(.VersionId)"' | \
    while IFS=$'\t' read -r key version_id; do
        if [ -n "$key" ] && [ -n "$version_id" ]; then
            aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version_id" --region "$REGION" 2>/dev/null || true
        fi
    done

    # Delete all delete markers
    aws s3api list-object-versions --bucket "$bucket" --region "$REGION" --output json 2>/dev/null | \
    jq -r '.DeleteMarkers[]? | "\(.Key)\t\(.VersionId)"' | \
    while IFS=$'\t' read -r key version_id; do
        if [ -n "$key" ] && [ -n "$version_id" ]; then
            aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version_id" --region "$REGION" 2>/dev/null || true
        fi
    done

    # Delete any remaining objects (non-versioned)
    aws s3 rm "s3://$bucket" --recursive --region "$REGION" 2>/dev/null || true
}

# Get all S3 buckets from the stack and nested stacks
echo ""
echo "Finding S3 buckets..."

BUCKETS=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "StackResources[?ResourceType=='AWS::S3::Bucket'].PhysicalResourceId" \
    --output text 2>/dev/null || echo "")

NESTED_STACKS=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "StackResources[?ResourceType=='AWS::CloudFormation::Stack'].PhysicalResourceId" \
    --output text 2>/dev/null || echo "")

for nested_stack in $NESTED_STACKS; do
    if [ -n "$nested_stack" ]; then
        NESTED_BUCKETS=$(aws cloudformation describe-stack-resources \
            --stack-name "$nested_stack" \
            --region "$REGION" \
            --query "StackResources[?ResourceType=='AWS::S3::Bucket'].PhysicalResourceId" \
            --output text 2>/dev/null || echo "")
        BUCKETS="$BUCKETS $NESTED_BUCKETS"
    fi
done

# Empty each bucket
for bucket in $BUCKETS; do
    if [ -n "$bucket" ]; then
        empty_bucket "$bucket"
    fi
done

# Delete the CloudFormation stack
echo ""
echo "Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"

echo "Waiting for stack deletion (this may take several minutes)..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"

echo ""
echo "Stack deleted successfully!"
