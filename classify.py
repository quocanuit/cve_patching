import boto3
import pandas as pd
import json
import time
from tqdm import tqdm
from botocore.exceptions import ClientError
import random
import logging
from datetime import datetime
import os

# Lấy từ môi trường (do Jenkins truyền vào), nếu không có thì dùng default
INPUT_CSV = os.environ.get("CLASSIFY_INPUT", "latest_cves_patch.csv")
OUTPUT_CSV = os.environ.get("CLASSIFY_OUTPUT", "updated_cves_patch.csv")

BEDROCK_REGION = "ap-southeast-2"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"  # Haiku nhanh hơn, ít throttling hơn

SEVERITY_LEVELS = ["Low", "Important", "Critical"]

# Aggressive rate limiting để tránh throttling
BASE_DELAY = 3.0  # Tăng delay cơ bản lên 3 giây
MAX_RETRIES = 3   # Giảm retry
BACKOFF_FACTOR = 3  # Tăng backoff factor
MAX_DELAY = 120   # Tăng max delay
JITTER_RANGE = 1.0  # Random jitter

# Checkpoint để save progress
CHECKPOINT_INTERVAL = 5  # Save sau mỗi 5 items
CHECKPOINT_FILE = "./checkpoint_progress.json"

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# ========================

# Tạo client Bedrock Runtime
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def save_checkpoint(processed_items, checkpoint_file):
    """Lưu progress để có thể resume"""
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'processed_items': processed_items,
                'timestamp': datetime.now().isoformat()
            }, f)
    except Exception as e:
        logger.warning(f"Could not save checkpoint: {e}")

def load_checkpoint(checkpoint_file):
    """Load progress từ checkpoint"""
    try:
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
            return data.get('processed_items', {})
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning(f"Could not load checkpoint: {e}")
        return {}

def ask_bedrock_conservative(details: str) -> str:
    """
    Phiên bản rất conservative để tránh throttling với improved prompt
    """
    # Cắt ngắn details để giảm token
    if len(details) > 1200:
        details = details[:1200] + "..."
    
    # Improved prompt với context và examples
    prompt = f"""You are a cybersecurity expert analyzing CVE (Common Vulnerabilities and Exposures) severity.

Based on the CVE details below, classify the severity level as exactly one of: Low, Important, or Critical

SEVERITY GUIDELINES:
- Critical: Remote code execution, arbitrary code execution, privilege escalation, authentication bypass, SQL injection, buffer overflow
- Important: Information disclosure, denial of service, cross-site scripting (XSS), CSRF, input validation bypass
- Low: Minor information leaks, configuration issues, low-impact vulnerabilities

CVE Details:
{details}

Classification:"""
    
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "max_tokens": 15,  # Tăng lên một chút cho response tốt hơn
        "temperature": 0,
        "top_p": 0.9,
    }

    # Retry với exponential backoff aggressive
    for attempt in range(MAX_RETRIES):
        try:
            # Delay trước mỗi request
            if attempt > 0:
                # Exponential backoff với jitter
                delay = min(
                    BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, JITTER_RANGE),
                    MAX_DELAY
                )
                logger.info(f"Retry {attempt}: Waiting {delay:.2f}s...")
                time.sleep(delay)
            else:
                # Delay cơ bản với jitter
                delay = BASE_DELAY + random.uniform(0, JITTER_RANGE)
                time.sleep(delay)

            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                accept="application/json",
                contentType="application/json",
                body=json.dumps(payload)
            )

            body = json.loads(response["body"].read())
            content = body.get("content", [])
            if isinstance(content, list):
                output = "".join([item.get("text", "") for item in content]).strip()
            else:
                output = str(content).strip()

            # Parse kết quả
            output_lower = output.lower()
            
            # Ưu tiên matching chính xác
            if "critical" in output_lower:
                return "Critical"
            elif "important" in output_lower:
                return "Important"
            elif "low" in output_lower:
                return "Low"
            
            # Fallback matching
            for level in SEVERITY_LEVELS:
                if level.lower() in output_lower:
                    return level
            
            # Nếu không parse được, dùng heuristic đơn giản
            if any(word in details.lower() for word in ['rce', 'remote code execution', 'arbitrary code']):
                return "Critical"
            elif any(word in details.lower() for word in ['privilege escalation', 'bypass', 'injection']):
                return "Important"
            else:
                return "Low"

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ThrottlingException':
                logger.warning(f"ThrottlingException on attempt {attempt + 1}/{MAX_RETRIES}: {error_message}")
                if attempt == MAX_RETRIES - 1:
                    logger.error("Max retries reached for ThrottlingException")
                    # Fallback heuristic
                    return fallback_classify(details)
                continue
            
            else:
                logger.error(f"API Error: {error_code} - {error_message}")
                if attempt == MAX_RETRIES - 1:
                    return fallback_classify(details)
                continue
                
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if attempt == MAX_RETRIES - 1:
                return fallback_classify(details)
            continue

    return fallback_classify(details)

def fallback_classify(details: str) -> str:
    """
    Improved fallback classification dựa trên CVE severity standards
    """
    details_lower = details.lower()
    
    # Critical severity indicators
    critical_keywords = [
        'remote code execution', 'rce', 'arbitrary code execution', 'code execution',
        'privilege escalation', 'escalation of privilege', 'gain elevated privileges',
        'authentication bypass', 'auth bypass', 'bypass authentication',
        'sql injection', 'command injection', 'code injection', 'script injection',
        'buffer overflow', 'heap overflow', 'stack overflow',
        'arbitrary file upload', 'file upload vulnerability',
        'deserialization', 'unsafe deserialization',
        'directory traversal', 'path traversal', 'lfi', 'rfi',
        'xxe', 'xml external entity', 'server-side request forgery', 'ssrf'
    ]
    
    # Important severity indicators  
    important_keywords = [
        'cross-site scripting', 'xss', 'reflected xss', 'stored xss',
        'cross-site request forgery', 'csrf', 'xsrf',
        'denial of service', 'dos', 'ddos', 'resource exhaustion',
        'information disclosure', 'information leak', 'data exposure',
        'session hijacking', 'session fixation',
        'input validation', 'validation bypass', 'filter bypass',
        'weak authentication', 'weak authorization',
        'clickjacking', 'ui redressing',
        'open redirect', 'unvalidated redirect'
    ]
    
    # Low severity indicators
    low_keywords = [
        'configuration', 'misconfiguration', 'default credentials',
        'information gathering', 'version disclosure',
        'weak encryption', 'deprecated protocol',
        'missing security header', 'security misconfiguration',
        'log injection', 'error message disclosure'
    ]
    
    # Check for critical first (highest priority)
    for keyword in critical_keywords:
        if keyword in details_lower:
            return "Critical"
    
    # Check for important
    for keyword in important_keywords:
        if keyword in details_lower:
            return "Important"
    
    # Check for low
    for keyword in low_keywords:
        if keyword in details_lower:
            return "Low"
    
    # Additional heuristics based on CVSS patterns
    if any(word in details_lower for word in ['cvss:3', 'cvss 3']):
        # Try to extract CVSS score if mentioned
        if any(word in details_lower for word in ['9.', '10.', 'critical']):
            return "Critical"
        elif any(word in details_lower for word in ['7.', '8.', 'high']):
            return "Important"
        elif any(word in details_lower for word in ['4.', '5.', '6.', 'medium']):
            return "Important"
        else:
            return "Low"
    
    # Default heuristic - if contains "vulnerability" or "exploit", likely Important
    if any(word in details_lower for word in ['vulnerability', 'exploit', 'attack']):
        return "Important"
    
    # Final fallback
    return "Low"

def classify_null_rows_with_checkpoint(csv_path: str, output_path: str):
    """
    Phiên bản với checkpoint để có thể resume
    """
    df = pd.read_csv(csv_path)

    if "Max Severity" not in df.columns or "Details (Link)" not in df.columns:
        raise ValueError("CSV must contain 'Max Severity' and 'Details (Link)' columns")

    # Load checkpoint
    processed_items = load_checkpoint(CHECKPOINT_FILE)
    logger.info(f"Loaded {len(processed_items)} processed items from checkpoint")

    # Chỉ xử lý những dòng có severity bị null và chưa được xử lý
    null_rows = df["Max Severity"].isnull()
    total_null = null_rows.sum()
    
    # Filter out đã xử lý
    remaining_indices = []
    for idx in df[null_rows].index:
        if str(idx) not in processed_items:
            remaining_indices.append(idx)
    
    remaining_count = len(remaining_indices)

    logger.info(f"Found {total_null} total null rows")
    logger.info(f"Remaining to process: {remaining_count}")
    logger.info(f"Using conservative rate limiting: {BASE_DELAY}s base delay")
    logger.info(f"Estimated time: {remaining_count * (BASE_DELAY + 1) / 60:.1f} minutes")
    
    if remaining_count == 0:
        logger.info("No remaining rows to process")
        return

    # Xử lý từng item
    processed_count = 0
    
    with tqdm(total=remaining_count, desc="Classifying CVEs") as pbar:
        for idx in remaining_indices:
            details = df.loc[idx, "Details (Link)"]
            
            try:
                severity = ask_bedrock_conservative(details)
                df.loc[idx, "Max Severity"] = severity
                processed_items[str(idx)] = severity
                
                processed_count += 1
                pbar.update(1)
                pbar.set_postfix({
                    "Current": severity, 
                    "Progress": f"{processed_count}/{remaining_count}",
                    "Total": f"{len(processed_items)}/{total_null}"
                })
                
                # Save checkpoint
                if processed_count % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(processed_items, CHECKPOINT_FILE)
                    logger.info(f"Checkpoint saved at {processed_count}/{remaining_count}")
                    
            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
                # Fallback
                severity = fallback_classify(details)
                df.loc[idx, "Max Severity"] = severity
                processed_items[str(idx)] = severity
                pbar.update(1)

    # Final save
    save_checkpoint(processed_items, CHECKPOINT_FILE)
    df.to_csv(output_path, index=False)
    
    logger.info(f"Output saved to {output_path}")
    logger.info(f"Processed {processed_count} new rows")
    logger.info(f"Total processed: {len(processed_items)}/{total_null}")

if __name__ == "__main__":
    print("Starting CVE classification with conservative rate limiting...")
    print("This will be slower but more reliable to avoid throttling.")
    print("Progress is saved every 5 items, so you can resume if interrupted.")
    
    classify_null_rows_with_checkpoint(INPUT_CSV, OUTPUT_CSV)
# Tạo client Bedrock Runtime
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def ask_bedrock(details: str) -> str:
    messages = [
        {
            "role": "user",
            "content": (
                "Given the following description of a CVE, classify its severity into one of three levels: "
                "Low, Important, or Critical. Only respond with one word: Low, Important, or Critical.\n\n"
                f"CVE Description:\n{details}"
            )
        }
    ]

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "max_tokens": 30,
        "temperature": 0.2,
        "top_p": 0.9,
    }

    # Retry logic với exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            # Thêm delay trước mỗi request (trừ lần đầu tiên)
            if attempt > 0:
                delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                print(f"[RETRY {attempt}] Waiting {delay:.2f} seconds before retry...")
                time.sleep(delay)
            else:
                # Delay cơ bản giữa các requests bình thường
                time.sleep(BASE_DELAY + random.uniform(0, 0.5))

            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                accept="application/json",
                contentType="application/json",
                body=json.dumps(payload)
            )

            body = json.loads(response["body"].read())
            content = body.get("content", [])
            if isinstance(content, list):
                output = "".join([item.get("text", "") for item in content]).strip()
            else:
                output = str(content).strip()

            # Kiểm tra kết quả hợp lệ
            for level in SEVERITY_LEVELS:
                if level.lower() in output.lower():
                    return level
            return "Low"  # fallback default

        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ThrottlingException':
                print(f"[WARNING] ThrottlingException on attempt {attempt + 1}/{MAX_RETRIES}")
                if attempt == MAX_RETRIES - 1:
                    print(f"[ERROR] Max retries reached for ThrottlingException")
                    return "Low"  # Fallback sau khi hết retry
                continue
            
            elif error_code == 'ValidationException':
                print(f"[ERROR] ValidationException: {e}")
                return "Low"
            
            else:
                print(f"[ERROR] Unexpected error: {e}")
                if attempt == MAX_RETRIES - 1:
                    return "Low"
                continue
                
        except Exception as e:
            print(f"[ERROR] Unexpected exception: {e}")
            if attempt == MAX_RETRIES - 1:
                return "Low"
            continue

    return "Low"  # Final fallback

def classify_null_rows(csv_path: str, output_path: str):
    """
    Đọc file CSV, fill vào các dòng có severity = null bằng model Bedrock.
    """
    df = pd.read_csv(csv_path)

    if "Max Severity" not in df.columns or "Details (Link)" not in df.columns:
        raise ValueError("CSV must contain 'Max Severity' and 'Details (Link)' columns")

    # Chỉ xử lý những dòng có severity bị null
    null_rows = df["Max Severity"].isnull()
    total_null = null_rows.sum()

    print(f"[INFO] Found {total_null} rows with null severity")
    print(f"[INFO] Using base delay of {BASE_DELAY}s between requests")
    print(f"[INFO] Estimated time: {total_null * BASE_DELAY / 60:.1f} minutes")

    if total_null == 0:
        print("[INFO] No null rows found, nothing to process")
        return

    # Xử lý từng dòng một cách tuần tự để tránh rate limiting
    processed_count = 0
    
    with tqdm(total=total_null, desc="Classifying CVEs") as pbar:
        for idx in df[null_rows].index:
            details = df.loc[idx, "Details (Link)"]
            severity = ask_bedrock(details)
            df.loc[idx, "Max Severity"] = severity
            
            processed_count += 1
            pbar.update(1)
            pbar.set_postfix({"Current": severity, "Progress": f"{processed_count}/{total_null}"})

    df.to_csv(output_path, index=False)
    print(f"[DONE] Output saved to {output_path}")
    print(f"[DONE] Processed {processed_count} rows successfully")

if __name__ == "__main__":
    classify_null_rows(INPUT_CSV, OUTPUT_CSV)