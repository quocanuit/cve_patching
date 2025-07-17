import boto3
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from typing import Dict, List, Any, Iterator
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import html

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedWindowsEventLogAnalyzer:
    def __init__(self, region_name='ap-southeast-2'):
        """
        Khởi tạo analyzer được tối ưu cho dữ liệu lớn
        """
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
        self.sns_client = boto3.client('sns', region_name=region_name)
        
        # Sử dụng Claude 3.5 Sonnet cho khả năng xử lý tốt
        self.model_id = "apac.anthropic.claude-3-5-sonnet-20240620-v1:0"
        
        # Các EventID được ưu tiên cao
        self.priority_events = {
            '1074', '6008', '7034', '1000', '1001', '4625', '4648'
        }
        
        # Cấu hình cho xử lý batch
        self.batch_size = 1000  # Xử lý 1000 events một lần
        self.max_ai_tokens = 3000  # Giới hạn token cho AI analysis
        
    def parse_xml_logs_streaming(self, file_path: str) -> Iterator[Dict]:
        """
        Parse XML logs theo kiểu streaming để tiết kiệm memory
        """
        try:
            # Đọc file theo chunks
            with open(file_path, 'r', encoding='utf-8') as file:
                buffer = ""
                in_event = False
                event_content = ""
                
                for line in file:
                    line = line.strip()
                    
                    if '<Event xmlns=' in line:
                        in_event = True
                        event_content = line
                    elif in_event:
                        event_content += line
                        
                        if '</Event>' in line:
                            # Parse single event
                            try:
                                event_data = self._parse_single_event(event_content)
                                if event_data:
                                    yield event_data
                            except Exception as e:
                                logger.warning(f"Error parsing event: {str(e)}")
                            
                            # Reset
                            in_event = False
                            event_content = ""
                            
        except Exception as e:
            logger.error(f"Error streaming XML file {file_path}: {str(e)}")
    
    def _parse_single_event(self, event_xml: str) -> Dict:
        """Parse một event XML đơn lẻ"""
        try:
            root = ET.fromstring(event_xml)
            ns = {'event': 'http://schemas.microsoft.com/win/2004/08/events/event'}
            
            return self._extract_event_data(root, ns)
            
        except Exception as e:
            logger.debug(f"Error parsing single event: {str(e)}")
            return None
    
    def _extract_event_data(self, event_elem, ns) -> Dict:
        """
        Trích xuất dữ liệu từ một Event element (tối ưu hóa)
        """
        try:
            system = event_elem.find('event:System', ns)
            rendering_info = event_elem.find('event:RenderingInfo', ns)
            
            # Chỉ lấy thông tin cần thiết
            data = {
                'event_id': '',
                'level': '',
                'time_created': '',
                'provider': '',
                'computer': '',
                'channel': '',
                'message': '',
                'level_text': ''
            }
            
            # System information
            if system is not None:
                event_id_elem = system.find('event:EventID', ns)
                if event_id_elem is not None:
                    data['event_id'] = event_id_elem.text
                
                level_elem = system.find('event:Level', ns)
                if level_elem is not None:
                    data['level'] = level_elem.text
                
                time_elem = system.find('event:TimeCreated', ns)
                if time_elem is not None:
                    data['time_created'] = time_elem.get('SystemTime', '')
                
                provider_elem = system.find('event:Provider', ns)
                if provider_elem is not None:
                    data['provider'] = provider_elem.get('Name', '')
                
                computer_elem = system.find('event:Computer', ns)
                if computer_elem is not None:
                    data['computer'] = computer_elem.text
                
                channel_elem = system.find('event:Channel', ns)
                if channel_elem is not None:
                    data['channel'] = channel_elem.text
            
            # Rendering information
            if rendering_info is not None:
                message_elem = rendering_info.find('event:Message', ns)
                if message_elem is not None:
                    data['message'] = message_elem.text
                
                level_text_elem = rendering_info.find('event:Level', ns)
                if level_text_elem is not None:
                    data['level_text'] = level_text_elem.text
            
            return data
            
        except Exception as e:
            logger.debug(f"Error extracting event data: {str(e)}")
            return None
    
    def analyze_logs_optimized(self, file_path: str) -> Dict:
        """
        Phân tích logs được tối ưu cho dữ liệu lớn
        """
        logger.info(f"Starting optimized analysis of {file_path}")
        
        # Counters cho analysis
        total_events = 0
        severity_count = Counter()
        event_id_count = Counter()
        hourly_count = defaultdict(int)
        provider_count = Counter()
        computer_count = Counter()
        
        # Lists cho events quan trọng
        critical_events = []
        error_events = []
        priority_events = []
        
        # Time tracking
        start_time = None
        end_time = None
        
        # Process streaming
        batch_count = 0
        for event in self.parse_xml_logs_streaming(file_path):
            if not event:
                continue
                
            total_events += 1
            batch_count += 1
            
            # Track time range
            if event.get('time_created'):
                try:
                    event_time = datetime.fromisoformat(event['time_created'].replace('Z', '+00:00'))
                    if start_time is None or event_time < start_time:
                        start_time = event_time
                    if end_time is None or event_time > end_time:
                        end_time = event_time
                    
                    # Hourly distribution
                    hourly_count[event_time.hour] += 1
                except:
                    pass
            
            # Severity analysis
            level = event.get('level', 'Unknown')
            severity_count[level] += 1
            
            # Event ID analysis
            event_id = event.get('event_id', 'Unknown')
            event_id_count[event_id] += 1
            
            # Provider analysis
            provider = event.get('provider', 'Unknown')
            provider_count[provider] += 1
            
            # Computer analysis
            computer = event.get('computer', 'Unknown')
            computer_count[computer] += 1
            
            # Collect critical events
            if level in ['1', '2']:  # Critical or Error
                if len(error_events) < 100:  # Giới hạn để tránh memory overflow
                    error_events.append({
                        'event_id': event_id,
                        'time': event.get('time_created', ''),
                        'message': event.get('message', '')[:200],  # Cắt ngắn message
                        'level': level,
                        'provider': provider
                    })
            
            # Collect priority events
            if event_id in self.priority_events:
                if len(priority_events) < 50:
                    priority_events.append({
                        'event_id': event_id,
                        'time': event.get('time_created', ''),
                        'message': event.get('message', '')[:200],
                        'computer': computer
                    })
            
            # Progress logging
            if batch_count % 1000 == 0:
                logger.info(f"Processed {batch_count} events...")
        
        # Compile results
        analysis = {
            'total_events': total_events,
            'time_range': {
                'start': start_time.isoformat() if start_time else 'Unknown',
                'end': end_time.isoformat() if end_time else 'Unknown',
                'duration_hours': (end_time - start_time).total_seconds() / 3600 if start_time and end_time else 0
            },
            'severity_distribution': self._convert_severity_levels(dict(severity_count)),
            'top_event_ids': self._format_top_events(event_id_count.most_common(10)),
            'critical_events': priority_events,
            'error_events': error_events,
            'hourly_distribution': dict(hourly_count),
            'provider_distribution': dict(provider_count.most_common(10)),
            'computer_analysis': dict(computer_count),
            'recommendations': []
        }
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_smart_recommendations(analysis)
        
        logger.info(f"Analysis completed. Total events: {total_events}")
        return analysis
    
    def _convert_severity_levels(self, severity_count: Dict) -> Dict:
        """Convert numeric levels to text"""
        severity_mapping = {
            '1': 'Critical',
            '2': 'Error',
            '3': 'Warning', 
            '4': 'Information',
            '5': 'Verbose'
        }
        
        converted = {}
        for level, count in severity_count.items():
            severity_name = severity_mapping.get(level, f'Level {level}')
            converted[severity_name] = count
        
        return converted
    
    def _format_top_events(self, top_events: List) -> List[Dict]:
        """Format top events with descriptions"""
        event_descriptions = {
            '1074': 'System Shutdown/Restart',
            '6008': 'Unexpected System Shutdown',
            '7034': 'Service Crashed',
            '1000': 'Application Error',
            '4625': 'Failed Logon',
            '4624': 'Successful Logon'
        }
        
        formatted = []
        for event_id, count in top_events:
            formatted.append({
                'event_id': event_id,
                'count': count,
                'description': event_descriptions.get(event_id, 'Unknown Event')
            })
        
        return formatted
    
    def _generate_smart_recommendations(self, analysis: Dict) -> List[str]:
        """Generate smart recommendations based on analysis"""
        recommendations = []
        
        # Check error rates
        total = analysis['total_events']
        severity = analysis['severity_distribution']
        
        error_rate = (severity.get('Critical', 0) + severity.get('Error', 0)) / total * 100 if total > 0 else 0
        
        if error_rate > 10:
            recommendations.append(f"Tỷ lệ lỗi cao: {error_rate:.1f}% - Cần kiểm tra ngay")
        elif error_rate > 5:
            recommendations.append(f"Tỷ lệ lỗi trung bình: {error_rate:.1f}% - Nên theo dõi")
        
        # Check for specific patterns
        if severity.get('Critical', 0) > 0:
            recommendations.append(f"Có {severity['Critical']} sự kiện nghiêm trọng cần xử lý")
        
        # Check time patterns
        hourly = analysis['hourly_distribution']
        if hourly:
            peak_hour = max(hourly.items(), key=lambda x: x[1])
            recommendations.append(f"Hoạt động cao nhất vào {peak_hour[0]}:00 với {peak_hour[1]} events")
        
        # Check for repeated errors
        top_events = analysis['top_event_ids']
        if top_events and top_events[0]['count'] > total * 0.1:
            recommendations.append(f"Event {top_events[0]['event_id']} xuất hiện quá nhiều ({top_events[0]['count']} lần)")
        
        return recommendations
    
    def generate_combined_ai_summary(self, app_analysis: Dict, sys_analysis: Dict) -> str:
        """
        Generate combined AI summary for both log types
        """
        # Tổng hợp dữ liệu từ cả hai loại logs
        total_events = app_analysis['total_events'] + sys_analysis['total_events']
        total_errors = (app_analysis['severity_distribution'].get('Error', 0) + 
                       app_analysis['severity_distribution'].get('Critical', 0) +
                       sys_analysis['severity_distribution'].get('Error', 0) + 
                       sys_analysis['severity_distribution'].get('Critical', 0))
        
        total_warnings = (app_analysis['severity_distribution'].get('Warning', 0) + 
                         sys_analysis['severity_distribution'].get('Warning', 0))
        
        prompt = f"""
Phân tích tổng hợp Windows Event Logs:

APPLICATION LOGS:
- Tổng: {app_analysis['total_events']:,} events
- Critical: {app_analysis['severity_distribution'].get('Critical', 0)}
- Error: {app_analysis['severity_distribution'].get('Error', 0)}
- Warning: {app_analysis['severity_distribution'].get('Warning', 0)}
- Top events: {[f"{e['event_id']}({e['count']})" for e in app_analysis['top_event_ids'][:3]]}

SYSTEM LOGS:
- Tổng: {sys_analysis['total_events']:,} events
- Critical: {sys_analysis['severity_distribution'].get('Critical', 0)}
- Error: {sys_analysis['severity_distribution'].get('Error', 0)}
- Warning: {sys_analysis['severity_distribution'].get('Warning', 0)}
- Top events: {[f"{e['event_id']}({e['count']})" for e in sys_analysis['top_event_ids'][:3]]}

TỔNG HỢP:
- Tổng events: {total_events:,}
- Tổng errors: {total_errors:,}
- Tổng warnings: {total_warnings:,}

Tạo báo cáo phân tích tổng hợp (tối đa 400 từ) bằng tiếng Việt:
1. Tình trạng tổng quan hệ thống
2. So sánh Application vs System logs
3. Các vấn đề nghiêm trọng cần xử lý
4. Khuyến nghị ưu tiên
"""
        
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                body=json.dumps(body),
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Error generating combined AI summary: {str(e)}")
            return f"Tổng quan: {total_events:,} events, {total_errors:,} lỗi cần xử lý trên toàn hệ thống."
    
    def _create_combined_email_report(self, app_analysis: Dict, sys_analysis: Dict, 
                                    ai_summary: str, processing_time: float) -> str:
        """Create combined email report for both log types"""
        
        total_events = app_analysis['total_events'] + sys_analysis['total_events']
        total_errors = (app_analysis['severity_distribution'].get('Error', 0) + 
                       app_analysis['severity_distribution'].get('Critical', 0) +
                       sys_analysis['severity_distribution'].get('Error', 0) + 
                       sys_analysis['severity_distribution'].get('Critical', 0))
        
        text_content = f"""
WINDOWS EVENT LOGS ANALYSIS REPORT
{'='*60}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Processing Time: {processing_time:.1f} seconds
Average Speed: {total_events/processing_time:.0f} events/second

AI SUMMARY - TỔNG HỢP
{'-'*40}
{ai_summary}

OVERVIEW - TỔNG QUAN
{'-'*40}
• Total Events Processed: {total_events:,}
• Total Critical + Errors: {total_errors:,}
• Total Warnings: {app_analysis['severity_distribution'].get('Warning', 0) + sys_analysis['severity_distribution'].get('Warning', 0):,}

APPLICATION LOGS ANALYSIS
{'-'*40}
• Total Events: {app_analysis['total_events']:,}
• Critical: {app_analysis['severity_distribution'].get('Critical', 0):,}
• Errors: {app_analysis['severity_distribution'].get('Error', 0):,}
• Warnings: {app_analysis['severity_distribution'].get('Warning', 0):,}
• Information: {app_analysis['severity_distribution'].get('Information', 0):,}

Top Application Events:"""
        
        for event in app_analysis['top_event_ids'][:5]:
            text_content += f"\n  • Event {event['event_id']}: {event['count']:,} times - {event['description']}"
        
        text_content += f"""

Application Recommendations:"""
        for i, rec in enumerate(app_analysis['recommendations'][:3], 1):
            text_content += f"\n  {i}. {rec}"
        
        text_content += f"""

SYSTEM LOGS ANALYSIS
{'-'*40}
• Total Events: {sys_analysis['total_events']:,}
• Critical: {sys_analysis['severity_distribution'].get('Critical', 0):,}
• Errors: {sys_analysis['severity_distribution'].get('Error', 0):,}
• Warnings: {sys_analysis['severity_distribution'].get('Warning', 0):,}
• Information: {sys_analysis['severity_distribution'].get('Information', 0):,}

Top System Events:"""
        
        for event in sys_analysis['top_event_ids'][:5]:
            text_content += f"\n  • Event {event['event_id']}: {event['count']:,} times - {event['description']}"
        
        text_content += f"""

System Recommendations:"""
        for i, rec in enumerate(sys_analysis['recommendations'][:3], 1):
            text_content += f"\n  {i}. {rec}"
        
        text_content += f"""

COMBINED ANALYSIS
{'-'*40}
Time Range: {app_analysis['time_range']['start'][:19]} to {app_analysis['time_range']['end'][:19]}
Duration: {app_analysis['time_range']['duration_hours']:.1f} hours

System Information:
• Total Computers (App): {len(app_analysis['computer_analysis'])}
• Total Computers (Sys): {len(sys_analysis['computer_analysis'])}
• Top App Providers: {', '.join(list(app_analysis['provider_distribution'].keys())[:3])}
• Top Sys Providers: {', '.join(list(sys_analysis['provider_distribution'].keys())[:3])}

SEVERITY COMPARISON
{'-'*40}
                 Application  |  System     |  Total
Critical:        {app_analysis['severity_distribution'].get('Critical', 0):>11,} | {sys_analysis['severity_distribution'].get('Critical', 0):>8,} | {app_analysis['severity_distribution'].get('Critical', 0) + sys_analysis['severity_distribution'].get('Critical', 0):>8,}
Error:           {app_analysis['severity_distribution'].get('Error', 0):>11,} | {sys_analysis['severity_distribution'].get('Error', 0):>8,} | {app_analysis['severity_distribution'].get('Error', 0) + sys_analysis['severity_distribution'].get('Error', 0):>8,}
Warning:         {app_analysis['severity_distribution'].get('Warning', 0):>11,} | {sys_analysis['severity_distribution'].get('Warning', 0):>8,} | {app_analysis['severity_distribution'].get('Warning', 0) + sys_analysis['severity_distribution'].get('Warning', 0):>8,}
Information:     {app_analysis['severity_distribution'].get('Information', 0):>11,} | {sys_analysis['severity_distribution'].get('Information', 0):>8,} | {app_analysis['severity_distribution'].get('Information', 0) + sys_analysis['severity_distribution'].get('Information', 0):>8,}

PRIORITY ACTIONS NEEDED
{'-'*40}"""
        
        # Combine and prioritize recommendations
        all_recommendations = []
        if app_analysis['severity_distribution'].get('Critical', 0) > 0:
            all_recommendations.append(f"🔴 CRITICAL: {app_analysis['severity_distribution']['Critical']} critical application events")
        if sys_analysis['severity_distribution'].get('Critical', 0) > 0:
            all_recommendations.append(f"🔴 CRITICAL: {sys_analysis['severity_distribution']['Critical']} critical system events")
        if total_errors > 100:
            all_recommendations.append(f"⚠️ HIGH: {total_errors} total errors across both logs")
        
        for i, rec in enumerate(all_recommendations[:5], 1):
            text_content += f"\n{i}. {rec}"
        
        text_content += f"""

---
Report generated by Optimized Windows Event Log Analyzer
Processed {total_events:,} events efficiently using streaming analysis.
Contact IT team for detailed investigation if critical issues found.
        """
        
        return text_content
    
    def process_large_log_files(self, app_log_path: str, sys_log_path: str, sns_topic_arn: str):
        """
        Process large log files efficiently and send single combined report
        """
        start_time = time.time()
        
        try:
            # Process both files in parallel
            logger.info("Starting parallel processing of log files...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit analysis tasks
                app_future = executor.submit(self.analyze_logs_optimized, app_log_path)
                sys_future = executor.submit(self.analyze_logs_optimized, sys_log_path)
                
                # Wait for completion
                app_analysis = app_future.result()
                sys_analysis = sys_future.result()
            
            # Generate combined AI summary
            logger.info("Generating combined AI summary...")
            ai_summary = self.generate_combined_ai_summary(app_analysis, sys_analysis)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create and send single combined report
            logger.info("Creating combined email report...")
            combined_email = self._create_combined_email_report(
                app_analysis, sys_analysis, ai_summary, processing_time
            )
            
            # Send single email notification
            total_events = app_analysis['total_events'] + sys_analysis['total_events']
            total_errors = (app_analysis['severity_distribution'].get('Error', 0) + 
                           app_analysis['severity_distribution'].get('Critical', 0) +
                           sys_analysis['severity_distribution'].get('Error', 0) + 
                           sys_analysis['severity_distribution'].get('Critical', 0))
            
            subject = f"Windows Event Logs Report - {total_events:,} events, {total_errors:,} errors - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            self.send_email_notification(sns_topic_arn, subject, combined_email)
            
            logger.info(f"Processing completed in {processing_time:.1f} seconds")
            logger.info(f"Combined report sent successfully")
            
        except Exception as e:
            logger.error(f"Error processing large log files: {str(e)}")
            raise
    
    def send_email_notification(self, topic_arn: str, subject: str, html_content: str):
        """Send email notification via SNS"""
        try:
            # Tạo text version đơn giản từ HTML
            text_content = self._html_to_text(html_content)
            
            # Gửi chỉ text content thay vì HTML để tránh lỗi rendering
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=subject,
                Message=text_content
            )
            
            logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text for email"""
        # Loại bỏ HTML tags và format lại
        import re
        
        # Loại bỏ CSS và script
        text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        
        # Thay thế các HTML tags thường gặp
        text = re.sub(r'<h[1-6][^>]*>', '\n=== ', text)
        text = re.sub(r'</h[1-6]>', ' ===\n', text)
        text = re.sub(r'<p[^>]*>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<br[^>]*>', '\n', text)
        text = re.sub(r'<li[^>]*>', '\n• ', text)
        text = re.sub(r'</li>', '', text)
        text = re.sub(r'<tr[^>]*>', '\n', text)
        text = re.sub(r'<td[^>]*>', ' | ', text)
        text = re.sub(r'</td>', '', text)
        text = re.sub(r'<th[^>]*>', ' | ', text)
        text = re.sub(r'</th>', '', text)
        
        # Loại bỏ tất cả HTML tags còn lại
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Làm sạch whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'^ +', '', text, flags=re.MULTILINE)
        
        return text.strip()

# Main function
def main():
    """Main function for large log processing"""
    # Configuration
    APP_LOG_PATH = "./EC2-Windows-ApplicationLogs.xml"
    SYS_LOG_PATH = "./EC2-Windows-SystemLogs.xml"
    SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:816069143343:report-to-mail"
    
    # Initialize optimized analyzer
    analyzer = OptimizedWindowsEventLogAnalyzer(region_name='ap-southeast-2')
    
    # Process large log files and send single combined report
    analyzer.process_large_log_files(APP_LOG_PATH, SYS_LOG_PATH, SNS_TOPIC_ARN)

if __name__ == "__main__":
    main()