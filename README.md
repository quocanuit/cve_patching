# CI/CD PIPELINE FOR AUTOMATING WINDOWS SECURITY PATCHING

## Overview

Manual Windows security patching creates significant risks: delayed remediation, human errors, inconsistent documentation, and poor scalability. Our solution provides a fully automated CI/CD pipeline that intelligently processes vulnerability reports and executes patches using AI-driven decision-making.

**Key Benefits:**
- AI-enhanced patching decisions using Amazon SageMaker
- Failure intelligence via Amazon Bedrock for log analysis and recommendations
- End-to-end traceability with comprehensive logging
- Event-driven automation requiring zero manual intervention

## Solution Architecture

![Level 2 Data Flow Diagram](./asset/image/data-flow-diagram.png)

### Workflow Stages

1. **Input**: Security team uploads CSV vulnerability report to S3
2. **Trigger**: S3 event automatically triggers Lambda → Jenkins pipeline
3. **Filter**: AWS Glue processes CSV, filtering Critical/High severity CVEs
4. **Classify**: Amazon Bedrock classifies unknown severity CVEs using LLM
5. **Predict**: SageMaker predicts patch duration and success probability
6. **Execute**: AWS Systems Manager runs PowerShell patches on Windows servers
7. **Analyze**: Bedrock analyzes patch logs and provides failure recommendations
8. **Report**: Summary emailed to security team with results and insights

## Technical Architecture

![AWS Diagram](./asset/image/aws-diagram.png)

### Core Components

- **Amazon S3**: Secure storage for vulnerability reports
- **AWS Lambda**: Event-driven pipeline triggering
- **Jenkins on EC2**: Central CI/CD orchestration
- **AWS Glue**: Serverless ETL for data processing
- **Amazon Bedrock**: AI classification and log analysis
- **Amazon SageMaker**: ML-based patch outcome prediction
- **AWS Systems Manager**: Secure remote patch execution
- **Amazon CloudWatch**: Comprehensive logging and monitoring
- **Amazon SNS**: Automated report delivery

## Impact

This solution transforms manual, error-prone patching into an intelligent, automated process that:
- Reduces vulnerability exposure time
- Eliminates human errors in patch prioritization
- Provides complete audit trails
- Scales efficiently across large Windows environments
- Uses AI to optimize patching decisions and troubleshoot failures
