#!/usr/bin/env python3
"""
Deployment Health Monitor
Checks for IAM permission issues, deployment failures, and application health
Can be run as a cron job for continuous monitoring
"""

import os
import sys
import time
import json
import subprocess
import requests
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class HealthMonitor:
    def __init__(self):
        self.project_id = "nytex-business-systems"
        self.service_name = "nytex-dashboard"
        self.region = "us-central1"
        self.production_url = "https://nytex-dashboard-nndn66l4ua-uc.a.run.app"
        self.github_repo = "josh0312/nytex_dashboard"
        
        # Service accounts
        self.compute_sa = "932676587025-compute@developer.gserviceaccount.com"
        self.github_sa = "github-actions@nytex-business-systems.iam.gserviceaccount.com"
        
        self.issues = []
        self.warnings = []
        
    def log(self, level, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_command(self, cmd, description):
        """Run command and return result"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.log("ERROR", f"Command '{description}' failed: {e}")
            return False, "", str(e)
    
    def check_iam_permissions(self):
        """Check if IAM permissions are properly configured"""
        self.log("INFO", "Checking IAM permissions...")
        
        # Check if GitHub Actions service account can act as compute service account
        cmd = f"gcloud iam service-accounts get-iam-policy {self.compute_sa} --format=json"
        success, output, error = self.run_command(cmd, "Get IAM policy")
        
        if not success:
            self.issues.append(f"Cannot access IAM policy for compute service account: {error}")
            return False
        
        try:
            policy = json.loads(output)
            bindings = policy.get('bindings', [])
            
            # Look for serviceAccountUser role
            for binding in bindings:
                if binding.get('role') == 'roles/iam.serviceAccountUser':
                    members = binding.get('members', [])
                    if f"serviceAccount:{self.github_sa}" in members:
                        self.log("INFO", "✅ IAM permissions are correctly configured")
                        return True
            
            self.issues.append("❌ GitHub Actions service account missing serviceAccountUser role")
            return False
            
        except json.JSONDecodeError:
            self.issues.append("❌ Could not parse IAM policy JSON")
            return False
    
    def check_cloud_run_service(self):
        """Check Cloud Run service status"""
        self.log("INFO", "Checking Cloud Run service...")
        
        cmd = f"gcloud run services describe {self.service_name} --region={self.region} --format=json"
        success, output, error = self.run_command(cmd, "Describe Cloud Run service")
        
        if not success:
            self.issues.append(f"❌ Cannot access Cloud Run service: {error}")
            return False
        
        try:
            service = json.loads(output)
            status = service.get('status', {})
            
            # Check if service is ready
            conditions = status.get('conditions', [])
            ready_condition = next((c for c in conditions if c.get('type') == 'Ready'), None)
            
            if ready_condition and ready_condition.get('status') == 'True':
                self.log("INFO", "✅ Cloud Run service is ready")
                
                # Get current revision
                traffic = status.get('traffic', [])
                if traffic:
                    active_revision = traffic[0].get('revisionName', 'unknown')
                    percent = traffic[0].get('percent', 0)
                    self.log("INFO", f"Active revision: {active_revision} ({percent}% traffic)")
                
                return True
            else:
                reason = ready_condition.get('message', 'Unknown') if ready_condition else 'No ready condition'
                self.issues.append(f"❌ Cloud Run service not ready: {reason}")
                return False
                
        except json.JSONDecodeError:
            self.issues.append("❌ Could not parse Cloud Run service JSON")
            return False
    
    def check_application_health(self):
        """Check if the application is responding correctly"""
        self.log("INFO", "Checking application health...")
        
        try:
            response = requests.get(self.production_url, timeout=30, allow_redirects=False)
            
            # Accept 200 (OK) or 302 (redirect for auth)
            if response.status_code in [200, 302]:
                self.log("INFO", f"✅ Application healthy (HTTP {response.status_code})")
                return True
            else:
                self.issues.append(f"❌ Application unhealthy (HTTP {response.status_code})")
                return False
                
        except requests.RequestException as e:
            self.issues.append(f"❌ Application unreachable: {e}")
            return False
    
    def check_recent_deployments(self):
        """Check for recent deployment failures"""
        self.log("INFO", "Checking recent deployments...")
        
        try:
            # Get recent workflow runs
            response = requests.get(
                f"https://api.github.com/repos/{self.github_repo}/actions/runs?per_page=5",
                timeout=10
            )
            
            if response.status_code != 200:
                self.warnings.append(f"⚠️  Cannot access GitHub Actions API (status {response.status_code})")
                return True  # Not critical
            
            runs = response.json().get('workflow_runs', [])
            
            # Check last 3 runs for failures
            failed_runs = []
            for run in runs[:3]:
                if run.get('conclusion') == 'failure':
                    run_number = run.get('run_number')
                    created_at = run.get('created_at')
                    failed_runs.append(f"#{run_number} ({created_at})")
            
            if failed_runs:
                self.warnings.append(f"⚠️  Recent deployment failures: {', '.join(failed_runs)}")
            else:
                self.log("INFO", "✅ No recent deployment failures")
            
            return True
            
        except requests.RequestException as e:
            self.warnings.append(f"⚠️  Cannot check GitHub Actions: {e}")
            return True  # Not critical
    
    def check_database_connectivity(self):
        """Check if the application can connect to the database"""
        self.log("INFO", "Checking database connectivity...")
        
        # Try to access a simple endpoint that would require DB access
        # This is a basic check - could be enhanced with a dedicated health endpoint
        try:
            response = requests.get(f"{self.production_url}/api/health", timeout=15)
            
            if response.status_code == 200:
                self.log("INFO", "✅ Database connectivity appears healthy")
                return True
            elif response.status_code == 404:
                # Health endpoint doesn't exist, that's ok for now
                self.log("INFO", "ℹ️  No dedicated health endpoint (this is ok)")
                return True
            else:
                self.warnings.append(f"⚠️  Health endpoint returned HTTP {response.status_code}")
                return True  # Not critical
                
        except requests.RequestException as e:
            self.warnings.append(f"⚠️  Cannot check database connectivity: {e}")
            return True  # Not critical
    
    def auto_fix_iam_permissions(self):
        """Automatically fix IAM permission issues"""
        self.log("INFO", "Attempting to fix IAM permissions...")
        
        cmd = f"""gcloud iam service-accounts add-iam-policy-binding {self.compute_sa} \
--member="serviceAccount:{self.github_sa}" \
--role="roles/iam.serviceAccountUser" \
--quiet"""
        
        success, output, error = self.run_command(cmd, "Fix IAM permissions")
        
        if success:
            self.log("INFO", "✅ IAM permissions fixed successfully")
            return True
        else:
            self.log("ERROR", f"❌ Failed to fix IAM permissions: {error}")
            return False
    
    def generate_report(self):
        """Generate a monitoring report"""
        report = []
        report.append("=" * 60)
        report.append("NyTex Dashboard - Deployment Health Report")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Production URL: {self.production_url}")
        report.append("")
        
        if self.issues:
            report.append("🚨 CRITICAL ISSUES:")
            for issue in self.issues:
                report.append(f"  {issue}")
            report.append("")
        
        if self.warnings:
            report.append("⚠️  WARNINGS:")
            for warning in self.warnings:
                report.append(f"  {warning}")
            report.append("")
        
        if not self.issues and not self.warnings:
            report.append("✅ ALL SYSTEMS HEALTHY")
            report.append("")
        
        report.append("Monitoring completed successfully.")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def run_full_check(self, auto_fix=False):
        """Run all health checks"""
        self.log("INFO", "Starting deployment health monitoring...")
        
        checks = [
            ("IAM Permissions", self.check_iam_permissions),
            ("Cloud Run Service", self.check_cloud_run_service),
            ("Application Health", self.check_application_health),
            ("Recent Deployments", self.check_recent_deployments),
            ("Database Connectivity", self.check_database_connectivity),
        ]
        
        all_healthy = True
        
        for check_name, check_func in checks:
            try:
                if not check_func():
                    all_healthy = False
                    
                    # Auto-fix IAM permissions if enabled
                    if auto_fix and check_name == "IAM Permissions":
                        if self.auto_fix_iam_permissions():
                            # Re-run the check
                            self.issues = [i for i in self.issues if "IAM" not in i]
                            if self.check_iam_permissions():
                                all_healthy = True
                        
            except Exception as e:
                self.issues.append(f"❌ {check_name} check failed: {e}")
                all_healthy = False
        
        # Generate and display report
        report = self.generate_report()
        print(report)
        
        # Save report to file
        report_file = project_root / "logs" / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(report)
        
        return all_healthy

def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor deployment health')
    parser.add_argument('--auto-fix', action='store_true', 
                       help='Automatically fix IAM permission issues')
    parser.add_argument('--continuous', type=int, metavar='MINUTES',
                       help='Run continuously, checking every N minutes')
    
    args = parser.parse_args()
    
    monitor = HealthMonitor()
    
    if args.continuous:
        print(f"Starting continuous monitoring (checking every {args.continuous} minutes)")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                monitor.run_full_check(auto_fix=args.auto_fix)
                time.sleep(args.continuous * 60)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
    else:
        # Single check
        healthy = monitor.run_full_check(auto_fix=args.auto_fix)
        sys.exit(0 if healthy else 1)

if __name__ == "__main__":
    main() 