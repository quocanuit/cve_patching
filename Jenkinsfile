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
        stage('Install Dependencies') {
            steps {
                script {
                    sh """
                        python3 -m ensurepip --upgrade
                        aws s3 cp s3://cve-bucket-abh/requirements.txt requirements.txt --region ap-southeast-2
                        python3 -m pip install -r requirements.txt
                    """
                }
            }
        }

        stage('Analyse Logs') {
            steps {
                script {
                    sh """
                        aws s3 cp s3://cve-bucket-abh/bedrock-analyse-logs.py bedrock-analyse-logs.py --region ap-southeast-2
                        python3 bedrock-analyse-logs.py
                    """
                }
            }
        }
    }

    post {
        success {
            echo "✅ Script executed successfully!"
        }
        failure {
            echo "Script execution failed!"
        }
    }
}
