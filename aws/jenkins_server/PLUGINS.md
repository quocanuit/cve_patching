# Jenkins Plugin Notes – CI/CD for Automated Windows Security Patching

## Purpose
This document lists the required additional Jenkins plugins (not included in the default "Suggested Plugins") needed to implement an automated CI/CD pipeline for vulnerability parsing, AI-based analysis, and patch deployment on Windows Server using AWS services.

---

## 🔌 Required Additional Plugins

### 🔹 AWS & Cloud Integration

| Plugin | Description |
|--------|-------------|
| **Pipeline: AWS Steps** | Provides native support for AWS-related steps in scripted or declarative pipelines. |
| **Amazon EC2 Plugin** *(optional)* | Allows Jenkins to manage dynamic build agents on Amazon EC2 instances. Useful if you want scalable agents. |

### 🔹 Data Processing & File Handling

| Plugin | Description |
|--------|-------------|
| **Pipeline Utility Steps Plugin** | Adds functions to read/write CSV, JSON, and other file types (e.g., `readCSV`, `readJSON`, `writeJSON`). Required for handling vulnerability data and patch plans. |

### 🔹 Event Triggers (Optional)

| Plugin | Description |
|--------|-------------|
| **Generic Webhook Trigger Plugin** *(optional)* | Enables Jenkins jobs to be triggered via HTTP webhook (e.g., from AWS Lambda or S3 event), instead of calling the Jenkins API directly. |
| **Parameterized Trigger Plugin** *(recommended)* | Supports triggering jobs with custom parameters between pipeline stages. |

### 🔹 Security & Credentials

| Plugin | Description |
|--------|-------------|
| **Mask Passwords Plugin** | Hides sensitive information like API keys or secrets from Jenkins logs. |

### 🔹 Others Plugins
| Plugin | Description |
|--------|-------------|
| **Pipeline: Stage View Plugin** | Provides a visual representation of the stages and status of each step in a Jenkins pipeline, making it easier to track progress and identify issues. |
| **Blue Ocean Plugin** | Offers a modern, user-friendly interface for Jenkins, making it easier to manage and visualize CI/CD pipelines with an intuitive and attractive experience. |