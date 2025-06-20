"""
Notification Service for NYTEX Sync System
"""

import os
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from jinja2 import Template
import json

# Google Secret Manager integration
try:
    from google.cloud import secretmanager
    from google.api_core import exceptions as gcp_exceptions
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class NotificationChannel:
    """Configuration for a notification channel"""
    name: str
    enabled: bool = True
    # Email specific
    smtp_server: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender_email: str = ""
    sender_name: str = "NYTEX Sync System"
    # Recipients
    recipients: List[str] = field(default_factory=list)
    # Rate limiting
    max_notifications_per_hour: int = 10
    last_notification_times: List[datetime] = field(default_factory=list)

@dataclass
class NotificationMessage:
    """A notification message to be sent"""
    subject: str
    body_text: str
    body_html: str = ""
    priority: str = "normal"  # low, normal, high, critical
    category: str = "general"  # sync_failure, sync_success, system_alert
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotificationConfig:
    """Configuration for notification service"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    recipients: List[str] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []

class NotificationService:
    """Service for sending notifications about sync events"""
    
    def __init__(self, config_file: str = None):
        """Initialize notification service"""
        self.channels = {}
        self.templates = {}
        self._load_configuration(config_file)
        self._load_templates()
    
    def _load_configuration(self, config_file: str = None):
        """Load notification configuration from environment or file"""
        # Default email channel from environment variables
        email_channel = NotificationChannel(
            name="email",
            enabled=os.getenv('SYNC_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            username=os.getenv('SMTP_USERNAME', ''),
            password=os.getenv('SMTP_PASSWORD', ''),
            sender_email=os.getenv('SMTP_SENDER_EMAIL', ''),
            sender_name=os.getenv('SMTP_SENDER_NAME', 'NYTEX Sync System'),
            recipients=self._parse_recipients(os.getenv('SYNC_NOTIFICATION_RECIPIENTS', '')),
            max_notifications_per_hour=int(os.getenv('NOTIFICATION_RATE_LIMIT', '10'))
        )
        
        self.channels['email'] = email_channel
        
        # Load additional channels from config file if provided
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Process additional channels from config file
                    for channel_config in config.get('channels', []):
                        channel = NotificationChannel(**channel_config)
                        self.channels[channel.name] = channel
            except Exception as e:
                logger.warning(f"Could not load notification config file {config_file}: {e}")
    
    def _parse_recipients(self, recipients_str: str) -> List[str]:
        """Parse comma-separated recipient list"""
        if not recipients_str:
            return []
        return [email.strip() for email in recipients_str.split(',') if email.strip()]
    
    def _load_templates(self):
        """Load email templates"""
        self.templates = {
            'sync_failure': {
                'subject': '[NYTEX {{ environment.upper() }} ALERT] 🚨 Sync Failure - {{ data_types|join(", ") }}',
                'text': '''
NYTEX Square Data Sync Failure Alert

Time: {{ timestamp }}
Environment: {{ environment.upper() }}
Failed Data Types: {{ data_types|join(", ") }}

{% for data_type, result in results.items() %}
{% if not result.success %}
=== {{ data_type.upper() }} SYNC FAILURE ===
Duration: {{ result.duration_seconds }}s
Records Processed: {{ result.records_processed }}
Errors:
{% for error in result.errors %}
  - {{ error }}
{% endfor %}

{% endif %}
{% endfor %}

Total Failed Syncs: {{ failed_count }}
Total Successful Syncs: {{ success_count }}

Please investigate and resolve these issues immediately.

System Details:
- Server: {{ server_info }}
- Database: {{ database_info }}
- Last Successful Sync: {{ last_successful_sync }}

Emergency Procedures:
1. Check logs: tail -f logs/sync_orchestrator.log
2. Manual sync: python scripts/sync_orchestrator.py --force
3. Emergency recovery: python direct_orders_sync.py

This is an automated alert from the NYTEX Sync System.
                ''',
                'html': '''
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #dc3545; color: white; padding: 15px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .failure { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .details { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .error-list { margin: 10px 0; padding-left: 20px; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
        .env-badge { background-color: #ffc107; color: #212529; padding: 4px 8px; border-radius: 3px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h2>🚨 NYTEX Sync Failure Alert</h2>
        <p>{{ timestamp }} - <span class="env-badge">{{ environment.upper() }}</span></p>
    </div>
    
    <div class="content">
        <p><strong>Failed Data Types:</strong> {{ data_types|join(", ") }}</p>
        
        {% for data_type, result in results.items() %}
        {% if not result.success %}
        <div class="failure">
            <h3>❌ {{ data_type.upper() }} SYNC FAILURE</h3>
            <p><strong>Duration:</strong> {{ result.duration_seconds }}s</p>
            <p><strong>Records Processed:</strong> {{ result.records_processed }}</p>
            <p><strong>Errors:</strong></p>
            <ul class="error-list">
            {% for error in result.errors %}
                <li>{{ error }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}
        {% endfor %}
        
        <div class="details">
            <h3>Summary</h3>
            <p><strong>Failed Syncs:</strong> {{ failed_count }}</p>
            <p><strong>Successful Syncs:</strong> {{ success_count }}</p>
            <p><strong>Server:</strong> {{ server_info }}</p>
            <p><strong>Database:</strong> {{ database_info }}</p>
            <p><strong>Last Successful Sync:</strong> {{ last_successful_sync }}</p>
        </div>
        
        <div class="details">
            <h3>🚨 Emergency Procedures</h3>
            <ol>
                <li>Check logs: <code>tail -f logs/sync_orchestrator.log</code></li>
                <li>Manual sync: <code>python scripts/sync_orchestrator.py --force</code></li>
                <li>Emergency recovery: <code>python direct_orders_sync.py</code></li>
            </ol>
        </div>
    </div>
    
    <div class="footer">
        <p>This is an automated alert from the NYTEX Sync System.</p>
    </div>
</body>
</html>
                '''
            },
            'sync_success': {
                'subject': '[NYTEX {{ environment.upper() }}] ✅ SUCCESS - Daily Sync Complete ({{ total_records }} records)',
                'text': '''
NYTEX Square Data Sync - Daily Summary

Time: {{ timestamp }}
Environment: {{ environment.upper() }}
Total Duration: {{ total_duration }}

{{ success_message }}

{% if not is_system_check %}
=== SYNC RESULTS ===
{% for data_type, result in results.items() %}
{{ data_type.upper() }}: ✅ SUCCESS
  - Records: {{ result.records_processed }} ({{ result.records_added }} new, {{ result.records_updated }} updated)
  - Duration: {{ result.duration_seconds }}s
{% endfor %}

=== SUMMARY ===
Total Records Processed: {{ total_records }}
Total New Records: {{ total_added }}
Total Updated Records: {{ total_updated }}
Average Processing Time: {{ avg_duration }}s

All syncs completed successfully. System is healthy.
{% else %}
=== SYSTEM STATUS ===
The automated sync system is running correctly.
No data synchronization was required at this time.
All sync schedules are being monitored properly.
{% endif %}

This is an automated report from the NYTEX Sync System.
                ''',
                'html': '''
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #28a745; color: white; padding: 15px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .success { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
        .env-badge { background-color: #17a2b8; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .success-banner { background-color: #d4edda; border: 2px solid #28a745; padding: 15px; border-radius: 10px; text-align: center; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h2>✅ NYTEX Daily Sync Complete</h2>
        <p>{{ timestamp }} - <span class="env-badge">{{ environment.upper() }}</span></p>
    </div>
    
    <div class="content">
        <div class="success-banner">
            <h2 style="color: #28a745; margin: 0;">{{ success_message }}</h2>
        </div>
        
        <div class="summary">
            <h3>📊 Summary</h3>
            <p><strong>Total Duration:</strong> {{ total_duration }}</p>
            {% if not is_system_check %}
            <p><strong>Total Records:</strong> {{ total_records }}</p>
            <p><strong>New Records:</strong> {{ total_added }}</p>
            <p><strong>Updated Records:</strong> {{ total_updated }}</p>
            {% else %}
            <p><strong>System Status:</strong> Healthy and Running</p>
            <p><strong>Sync Status:</strong> No syncs due at this time</p>
            <p><strong>Monitoring:</strong> Active</p>
            {% endif %}
        </div>
        
        {% if not is_system_check %}
        <h3>📋 Detailed Results</h3>
        <table>
            <tr>
                <th>Data Type</th>
                <th>Status</th>
                <th>Records</th>
                <th>New</th>
                <th>Updated</th>
                <th>Duration</th>
            </tr>
            {% for data_type, result in results.items() %}
            <tr>
                <td>{{ data_type.upper() }}</td>
                <td>✅ SUCCESS</td>
                <td>{{ result.records_processed }}</td>
                <td>{{ result.records_added }}</td>
                <td>{{ result.records_updated }}</td>
                <td>{{ result.duration_seconds }}s</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
        
        <div class="success">
            {% if not is_system_check %}
            <p><strong>🎉 All syncs completed successfully!</strong></p>
            <p>System is healthy and all data is up to date.</p>
            {% else %}
            <p><strong>🔍 System check completed successfully!</strong></p>
            <p>Automated sync system is running correctly and monitoring all schedules.</p>
            {% endif %}
        </div>
    </div>
    
    <div class="footer">
        <p>This is an automated report from the NYTEX Sync System.</p>
    </div>
</body>
</html>
                '''
            },
            'system_alert': {
                'subject': '[NYTEX {{ environment.upper() }} SYSTEM] {{ alert_type }} - {{ title }}',
                'text': '''
NYTEX System Alert

Alert Type: {{ alert_type }}
Title: {{ title }}
Time: {{ timestamp }}
Environment: {{ environment }}

Description:
{{ description }}

{% if details %}
Details:
{% for key, value in details.items() %}
  {{ key }}: {{ value }}
{% endfor %}
{% endif %}

{% if recommended_actions %}
Recommended Actions:
{% for action in recommended_actions %}
  - {{ action }}
{% endfor %}
{% endif %}

This is an automated alert from the NYTEX Sync System.
                ''',
                'html': '''
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #ffc107; color: #212529; padding: 15px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .alert { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .details { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .actions { background-color: #e2e3e5; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h2>⚠️ NYTEX System Alert</h2>
        <p>{{ alert_type }} - {{ timestamp }}</p>
    </div>
    
    <div class="content">
        <div class="alert">
            <h3>{{ title }}</h3>
            <p>{{ description }}</p>
        </div>
        
        {% if details %}
        <div class="details">
            <h3>Details</h3>
            {% for key, value in details.items() %}
            <p><strong>{{ key }}:</strong> {{ value }}</p>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if recommended_actions %}
        <div class="actions">
            <h3>Recommended Actions</h3>
            <ul>
            {% for action in recommended_actions %}
                <li>{{ action }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}
    </div>
    
    <div class="footer">
        <p>This is an automated alert from the NYTEX Sync System.</p>
    </div>
</body>
</html>
                '''
            }
        }
    
    def _can_send_notification(self, channel: NotificationChannel) -> bool:
        """Check if we can send a notification (rate limiting)"""
        if not channel.enabled:
            return False
        
        now = datetime.now()
        # Remove notifications older than 1 hour
        channel.last_notification_times = [
            t for t in channel.last_notification_times 
            if now - t < timedelta(hours=1)
        ]
        
        # Check if we're under the rate limit
        return len(channel.last_notification_times) < channel.max_notifications_per_hour
    
    def _record_notification_sent(self, channel: NotificationChannel):
        """Record that a notification was sent"""
        channel.last_notification_times.append(datetime.now())
    
    def _render_template(self, template_name: str, template_type: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context"""
        try:
            template_content = self.templates[template_name][template_type]
            template = Template(template_content)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}/{template_type}: {e}")
            return f"Error rendering template: {e}"
    
    def _send_email(self, channel: NotificationChannel, message: NotificationMessage) -> bool:
        """Send an email notification"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{channel.sender_name} <{channel.sender_email}>"
            msg['To'] = ', '.join(channel.recipients)
            msg['Subject'] = message.subject
            
            # Add text part
            text_part = MIMEText(message.body_text, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if available
            if message.body_html:
                html_part = MIMEText(message.body_html, 'html')
                msg.attach(html_part)
            
            # Add attachments
            for attachment in message.attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['data'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment["filename"]}'
                )
                msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(channel.smtp_server, channel.smtp_port)
            server.starttls()
            server.login(channel.username, channel.password)
            
            text = msg.as_string()
            server.sendmail(channel.sender_email, channel.recipients, text)
            server.quit()
            
            logger.info(f"Email notification sent to {len(channel.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def send_sync_failure_alert(self, results: Dict[str, Any], environment: str = "production") -> bool:
        """Send sync failure alert"""
        failed_results = {k: v for k, v in results.items() if not v.success}
        if not failed_results:
            return True  # No failures to report
        
        context = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'environment': environment,
            'results': results,
            'data_types': list(failed_results.keys()),
            'failed_count': len(failed_results),
            'success_count': len(results) - len(failed_results),
            'server_info': os.uname().nodename if hasattr(os, 'uname') else 'Unknown',
            'database_info': 'PostgreSQL (Cloud SQL)',
            'last_successful_sync': 'Check sync_state table'
        }
        
        # Render templates
        subject = self._render_template('sync_failure', 'subject', context)
        body_text = self._render_template('sync_failure', 'text', context)
        body_html = self._render_template('sync_failure', 'html', context)
        
        message = NotificationMessage(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            priority='critical',
            category='sync_failure',
            metadata={'failed_data_types': list(failed_results.keys())}
        )
        
        return self._send_notification(message)
    
    def send_sync_success_report(self, results: Dict[str, Any], environment: str = "production") -> bool:
        """Send daily sync success report"""
        # Check if this is a system check (no actual syncs)
        is_system_check = len(results) == 1 and 'system_check' in results
        
        total_records = sum(r.records_processed for r in results.values())
        total_added = sum(getattr(r, 'records_added', 0) for r in results.values())
        total_updated = sum(getattr(r, 'records_updated', 0) for r in results.values())
        total_duration = sum(getattr(r, 'duration_seconds', 0) for r in results.values())
        avg_duration = total_duration / len(results) if results else 0
        
        # Adjust subject and content for system check
        if is_system_check:
            subject_template = '[NYTEX {{ environment.upper() }}] ✅ SUCCESS - System Check (No syncs due)'
            success_message = "🔍 SYSTEM CHECK COMPLETED - No syncs were due at this time"
        else:
            subject_template = '[NYTEX {{ environment.upper() }}] ✅ SUCCESS - Daily Sync Complete ({{ total_records }} records)'
            success_message = "🎉 ALL SYNCS COMPLETED SUCCESSFULLY! 🎉"
        
        context = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'environment': environment,
            'results': results,
            'total_records': total_records,
            'total_added': total_added,
            'total_updated': total_updated,
            'total_duration': f"{total_duration:.1f}s",
            'avg_duration': f"{avg_duration:.1f}",
            'is_system_check': is_system_check,
            'success_message': success_message
        }
        
        # Use custom subject for system check, otherwise use template
        if is_system_check:
            template = Template(subject_template)
            subject = template.render(**context)
        else:
            subject = self._render_template('sync_success', 'subject', context)
        
        body_text = self._render_template('sync_success', 'text', context)
        body_html = self._render_template('sync_success', 'html', context)
        
        message = NotificationMessage(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            priority='normal',
            category='sync_success',
            metadata={'total_records': total_records, 'is_system_check': is_system_check}
        )
        
        return self._send_notification(message)
    
    def send_system_alert(self, alert_type: str, title: str, description: str, 
                         details: Dict[str, Any] = None, 
                         recommended_actions: List[str] = None,
                         environment: str = "production") -> bool:
        """Send system alert"""
        context = {
            'alert_type': alert_type,
            'title': title,
            'description': description,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'environment': environment,
            'details': details or {},
            'recommended_actions': recommended_actions or []
        }
        
        # Render templates
        subject = self._render_template('system_alert', 'subject', context)
        body_text = self._render_template('system_alert', 'text', context)
        body_html = self._render_template('system_alert', 'html', context)
        
        message = NotificationMessage(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            priority='high',
            category='system_alert',
            metadata={'alert_type': alert_type}
        )
        
        return self._send_notification(message)
    
    def _send_notification(self, message: NotificationMessage) -> bool:
        """Send notification through all enabled channels"""
        success = True
        
        for channel_name, channel in self.channels.items():
            if not self._can_send_notification(channel):
                logger.warning(f"Rate limit exceeded for channel {channel_name}")
                continue
            
            try:
                if channel_name == 'email':
                    sent = self._send_email(channel, message)
                    if sent:
                        self._record_notification_sent(channel)
                    success = success and sent
                else:
                    logger.warning(f"Unknown notification channel: {channel_name}")
                    
            except Exception as e:
                logger.error(f"Error sending notification via {channel_name}: {e}")
                success = False
        
        return success
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels"""
        results = {}
        
        test_message = NotificationMessage(
            subject="NYTEX Sync System - Test Notification",
            body_text="This is a test notification from the NYTEX Sync System. If you receive this, notifications are working correctly.",
            body_html="<p>This is a <strong>test notification</strong> from the NYTEX Sync System.</p><p>If you receive this, notifications are working correctly.</p>",
            priority='low',
            category='test'
        )
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                results[channel_name] = False
                continue
                
            try:
                if channel_name == 'email':
                    results[channel_name] = self._send_email(channel, test_message)
                else:
                    results[channel_name] = False
                    
            except Exception as e:
                logger.error(f"Test failed for channel {channel_name}: {e}")
                results[channel_name] = False
        
        return results


# Convenience functions for easy usage
def send_sync_failure_alert(results: Dict[str, Any], environment: str = "production") -> bool:
    """Convenience function to send sync failure alert"""
    service = NotificationService()
    return service.send_sync_failure_alert(results, environment)

def send_sync_success_report(results: Dict[str, Any], environment: str = "production") -> bool:
    """Convenience function to send sync success report"""
    service = NotificationService()
    return service.send_sync_success_report(results, environment)

def send_system_alert(alert_type: str, title: str, description: str, 
                     details: Dict[str, Any] = None, 
                     recommended_actions: List[str] = None,
                     environment: str = "production") -> bool:
    """Convenience function to send system alert"""
    service = NotificationService()
    return service.send_system_alert(alert_type, title, description, details, recommended_actions, environment)

def test_notifications() -> Dict[str, bool]:
    """Convenience function to test notifications"""
    service = NotificationService()
    return service.test_notifications() 