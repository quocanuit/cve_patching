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
        SNS_TOPIC             = 'report-to-mail'
        AWS_ACCOUNT_ID        = '816069143343'

        // Patch Configuration
        PATCH_GROUP           = 'my-target-group'
        PATCH_BASELINE_NAME   = 'custom-kb-baseline'
    }

    stages {
        stage('Initialize') {
            steps {
                script {
                    echo 'Initialize'
                    sh """
                        python3 -m ensurepip --upgrade
                        export HOME=/var/lib/jenkins
                        export PATH="\$HOME/.local/bin:\$PATH"
                        aws s3 cp s3://cve-bucket-abh/requirements.txt requirements.txt --region ap-southeast-2
                        python3 -m pip install -r requirements.txt
                    """
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
                    sh """
                        aws s3 cp s3://cve-bucket-abh/classify.py classify.py --region ap-southeast-2
                        python3 classify.py CLASSIFY_INPUT=latest_cves_patch.csv CLASSIFY_OUTPUT=updated_cves_patch.csv
                        echo "Uploading updated CSV to S3..."
                        aws s3 cp updated_cves_patch.csv s3://cve-bucket-abh/updated_csv/updated_cves_patch.csv --region ap-southeast-2
                    """
                }
            }
        }

        stage('Extract KB IDs from CSV') {
            steps {
                script {
                    def csv = readFile('updated_cves_patch.csv')
                    def kbSet = [] as Set

                    csv.split('\n').eachWithIndex { line, idx ->
                        if (idx == 0) return // Skip header
                        def columns = line.split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)/) // CSV-safe split
                        def downloadLink = columns.size() > 5 ? columns[5].trim().replaceAll('"', '') : ''
                        def matcher = downloadLink =~ /(KB\d{7})/
                        if (matcher.find()) {
                            kbSet << matcher.group(1)
                        }
                    }

                    if (kbSet.isEmpty()) {
                        error "No KB found in CSV!"
                    }

                    def top2 = kbSet.toList().take(2)
                    def approvedPatchesJson = "[" + top2.collect { "\"$it\"" }.join(',') + "]"
                    env.APPROVED_PATCHES_JSON = approvedPatchesJson
                    echo "Top 2 KB: ${approvedPatchesJson}"
                }
            }
        }

        stage('Create or Update Patch Baseline') {
            steps {
                script {
                    echo "Create or Update Patch Baseline..."

                    def baselineId = sh(
                        script: """
                            aws ssm describe-patch-baselines \
                            --filters "Key=NAME,Values=${PATCH_BASELINE_NAME}" \
                            --region ${AWS_REGION} \
                            --query "BaselineIdentities[0].BaselineId" \
                            --output text 2>/dev/null || true
                        """,
                        returnStdout: true
                    ).trim()

                    if (baselineId == "None" || baselineId == "") {
                        baselineId = sh(
                            script: """
                                aws ssm create-patch-baseline \
                                --name "${PATCH_BASELINE_NAME}" \
                                --approved-patches '${env.APPROVED_PATCHES_JSON}' \
                                --region ${AWS_REGION} \
                                --query "BaselineId" \
                                --output text
                            """,
                            returnStdout: true
                        ).trim()
                        echo "New Baseline created: ${baselineId}"
                    } else {
                        echo "Baseline existed: ${baselineId}"
                        sh """
                            aws ssm update-patch-baseline \
                            --baseline-id "${baselineId}" \
                            --approved-patches '${env.APPROVED_PATCHES_JSON}' \
                            --region ${AWS_REGION}
                        """
                        echo "Baseline updated."
                    }

                    env.BASELINE_ID = baselineId
                }
            }
        }

        stage('Register Patch Baseline with Patch Group') {
            steps {
                sh '''
                echo "Register Patch Baseline with Patch Group..."

                OLD_BASELINE_ID=$(aws ssm describe-patch-groups \
                  --region "$AWS_REGION" \
                  --query "Mappings[?PatchGroup=='${PATCH_GROUP}'].BaselineIdentity.BaselineId" \
                  --output text)

                if [ -n "$OLD_BASELINE_ID" ] && [ "$OLD_BASELINE_ID" != "${BASELINE_ID}" ]; then
                  echo "Deregistering old baseline: $OLD_BASELINE_ID"
                  aws ssm deregister-patch-baseline-for-patch-group \
                    --baseline-id "$OLD_BASELINE_ID" \
                    --patch-group "$PATCH_GROUP" \
                    --region "$AWS_REGION"
                fi

                aws ssm register-patch-baseline-for-patch-group \
                  --baseline-id "${BASELINE_ID}" \
                  --patch-group "$PATCH_GROUP" \
                  --region "$AWS_REGION"
                '''
            }
        }

        stage('Run Patch via SSM') {
            steps {
                sh '''
                aws ssm send-command \
                  --document-name "AWS-RunPatchBaseline" \
                  --targets "Key=tag:PatchGroup,Values=${PATCH_GROUP}" \
                  --parameters Operation=Install \
                  --comment "Apply KB patches from CSV via Jenkins" \
                  --region ${AWS_REGION}
                '''
            }
        }

        stage('Fetch Windows Server Logs') {
            steps {
                script {
                    echo 'Fetching Windows Server Logs from CloudWatch...'
                    def logDir = "/var/lib/jenkins/logs"
                    sh """
                        mkdir -p ${logDir}
                        export PYTHONIOENCODING=UTF-8
                        export PYTHONUTF8=1

                        # ApplicationLogs
                        aws logs filter-log-events \
                        --log-group-name EC2-Windows-ApplicationLogs \
                        --region ${AWS_REGION} \
                        --max-items 100 \
                        --query 'events[].message' \
                        --output text \
                        > "${logDir}/EC2-Windows-ApplicationLogs.txt"

                        echo "================ ApplicationLogs ================"
                        cat "${logDir}/EC2-Windows-ApplicationLogs.txt"

                        # SystemLogs
                        aws logs filter-log-events \
                        --log-group-name EC2-Windows-SystemLogs \
                        --region ${AWS_REGION} \
                        --max-items 100 \
                        --query 'events[].message' \
                        --output text \
                        > "${logDir}/EC2-Windows-SystemLogs.txt"

                        echo "================ SystemLogs ================"
                        cat "${logDir}/EC2-Windows-SystemLogs.txt"

                        echo "Logs saved to ${logDir}"
                    """
                }
            }
        }

        stage('Publish Logs via SNS') {
            steps {
                script {
                    def logDir = "/var/lib/jenkins/logs"
                    def bucket = "${S3_BUCKET}"
                    def currentDate = new Date().format("dd/MM/yyyy HH:mm:ss")
                    def buildInfo = "${env.JOB_NAME} - Build #${env.BUILD_NUMBER}"

                    // Upload Application Logs and generate presigned URL
                    def urlApp = sh(script: """
                        aws s3 cp "${logDir}/EC2-Windows-ApplicationLogs.txt" s3://${bucket}/jenkins-logs/EC2-Windows-ApplicationLogs.txt --region ${AWS_REGION}
                        aws s3 presign s3://${bucket}/jenkins-logs/EC2-Windows-ApplicationLogs.txt --expires-in 86400
                    """, returnStdout: true).trim()

                    // Upload System Logs and generate presigned URL
                    def urlSys = sh(script: """
                        aws s3 cp "${logDir}/EC2-Windows-SystemLogs.txt" s3://${bucket}/jenkins-logs/EC2-Windows-SystemLogs.txt --region ${AWS_REGION}
                        aws s3 presign s3://${bucket}/jenkins-logs/EC2-Windows-SystemLogs.txt --expires-in 86400
                    """, returnStdout: true).trim()

                    // Create professional email content
                    sh """
                        cat > message.txt <<EOF
Subject: Jenkins Build Report - EC2 Windows Logs Available

Dear Team,

The Jenkins build has completed successfully and the latest EC2 Windows logs are now available for download.

BUILD INFORMATION:
• Job Name: ${env.JOB_NAME}
• Build Number: #${env.BUILD_NUMBER}
• Build Status: ${currentBuild.result ?: 'SUCCESS'}
• Timestamp: ${currentDate}

LOG FILES AVAILABLE:
The following log files have been uploaded to S3 and are accessible via the secure links below:

1. Application Logs
Download: ${urlApp}

2. System Logs  
Download: ${urlSys}

IMPORTANT NOTES:
• These download links are valid for 24 hours from the time of generation
• The files are securely stored in S3 bucket: ${bucket}
• If you encounter any issues accessing the logs, please contact the DevOps team

For any questions or support, please reach out to the development team.

Best regards,
Jenkins Automation System
EOF
                    """

                    // Send notification via SNS
                    sh """
                        aws sns publish \
                        --topic-arn "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${SNS_TOPIC}" \
                        --subject "Jenkins Build Report - EC2 Windows Logs Available" \
                        --message file://message.txt \
                        --region ${AWS_REGION}
                    """
                }
            }
        }
    }

    post {
        always {
            echo 'Clean'
            cleanWs()
        }
    }
}