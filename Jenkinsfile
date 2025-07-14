pipeline {
    agent any
    
    environment {
        // AWS Access Credentials
        AWS_REGION            = 'ap-southeast-2'
        AWS_ACCESS_KEY_ID     = credentials('aws-access-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('aws-secret-access-key')

        // Resources Config
        S3_BUCKET             = 'cve-bucket-abh'
        GLUE_JOB_NAME         = 'filter-cve-job'
        S3_OUTPUT_PREFIX      = 'filtered_csv/'
    }
    
    stages {
        stage('Initialize') {
            steps {
                script {
                    echo 'Hello World'
                }
            }
        }
        
        stage('Identify Latest CSV in S3') {
            steps {
                script {
                    echo 'Looking up latest CSV in S3...'
                    def latestFile = sh(
                        script: $/
                            aws s3api list-objects-v2 \
                              --bucket "${S3_BUCKET}" \
                              --query 'reverse(sort_by(Contents[?ends_with(Key, `.csv`)], &LastModified))[:1].Key' \
                              --region "${AWS_REGION}" \
                              --output text
                        /$,
                        returnStdout: true
                    ).trim()
                    if (!latestFile || latestFile == "None") {
                        error "No CSV file found in bucket ${S3_BUCKET}"
                    }
                    echo "Latest CSV file in S3: ${latestFile}"
                    env.S3_INPUT_PATH = "s3://${S3_BUCKET}/${latestFile}"
                    env.S3_OUTPUT_PATH = "s3://${S3_BUCKET}/${S3_OUTPUT_PREFIX}"
                }
            }
        }

        stage('Run AWS Glue Job to Filter') {
            steps {
                script {
                    echo "Starting Glue Job: ${GLUE_JOB_NAME}"
                    def runId = sh(script: """
                        aws glue start-job-run \
                          --job-name "${GLUE_JOB_NAME}" \
                          --arguments '--input_path=${env.S3_INPUT_PATH},--output_path=${env.S3_OUTPUT_PATH}' \
                          --region ${AWS_REGION} \
                          --query 'JobRunId' \
                          --output text
                    """, returnStdout: true).trim()
                    echo "Glue JobRunId: ${runId}"
                    timeout(time: 20, unit: 'MINUTES') {
                        waitUntil {
                            sleep(time: 30, unit: 'SECONDS')
                            def state = sh(script: """
                                aws glue get-job-run \
                                  --job-name "${GLUE_JOB_NAME}" \
                                  --run-id "${runId}" \
                                  --region ${AWS_REGION} \
                                  --query 'JobRun.JobRunState' \
                                  --output text
                            """, returnStdout: true).trim()
                            echo "Glue job state: ${state}"
                            if (state == 'FAILED' || state == 'TIMEOUT') {
                                error "Glue job failed or timed out"
                            }
                            return state == 'SUCCEEDED'
                        }
                    }
                    echo "Glue job completed successfully"
                }
            }
        }

        stage('Download and Rename Output to CSV') {
            steps {
                script {
                    echo 'Downloading uncompressed CSV output from S3...'
                    def rawFile = sh(
                        script: """
                            aws s3 ls s3://${S3_BUCKET}/${S3_OUTPUT_PREFIX} --region ${AWS_REGION} | grep 'run-' | awk '{print \$4}' | head -n 1
                        """,
                        returnStdout: true
                    ).trim()
                    if (!rawFile) {
                        error "No output file found in ${S3_OUTPUT_PATH}"
                    }
                    echo "Found file: ${rawFile}"
                    sh """
                        aws s3 cp s3://${S3_BUCKET}/${S3_OUTPUT_PREFIX}${rawFile} latest_cves_patch.csv --region ${AWS_REGION}
                    """
                    if (!fileExists("latest_cves_patch.csv")) {
                        error "Failed to download or rename to latest_cves_patch.csv"
                    }
                    def fileSize = sh(script: "stat -c%s 'latest_cves_patch.csv'", returnStdout: true).trim()
                    echo "CSV downloaded and renamed: latest_cves_patch.csv (${fileSize} bytes)"
                }
            }
        }
        
        stage('Classify Unknown Severity') {
            steps {
                script {
                    echo 'Classify Unknown Severity'
                    // Use Amazon Bedrock to classify CVEs with unknown severity
                }
            }
        }
        
        stage('Predict Patch Duration (ML)') {
            steps {
                script {
                    echo 'Predict Patch Duration (ML)'
                    // Use SageMaker to predict patch duration and success probability
                }
            }
        }
        
        stage('Execute Patches') {
            steps {
                script {
                    echo 'Execute Patches'
                    // Execute patches on Windows servers using AWS SSM
                }
            }
        }
        
        stage('Analyze Results') {
            steps {
                script {
                    echo 'Analyze Results'
                    // Analyze patch results and generate execution report
                }
            }
        }
        
        stage('Generate Final Report') {
            steps {
                script {
                    echo 'Generate Final Report'
                    // Generate comprehensive HTML report and send notifications
                }
            }
        }
    }
    
    post {
        always {
            echo 'Clean'
            //
        }
    }
}