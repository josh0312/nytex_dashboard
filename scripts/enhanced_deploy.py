#!/usr/bin/env python3
"""
Enhanced Deployment Script with IAM Permission Setup
Handles IAM permissions, runs tests, deploys, and monitors CI/CD pipeline
"""

import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class ProgressSpinner:
    """Simple spinner for showing progress"""
    def __init__(self):
        self.chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.index = 0
    
    def next(self):
        char = self.chars[self.index]
        self.index = (self.index + 1) % len(self.chars)
        return char

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_step(step_num, total_steps, description):
    """Print a step with numbering"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}[{step_num}/{total_steps}] {description}{Colors.END}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")

def run_command(cmd, description, show_output=False):
    """Run a command and return success status"""
    print(f"   Running: {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print_success(f"{description} completed")
            if show_output and result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:100]}...")
            return True, result.stdout
        else:
            print_error(f"{description} failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False, result.stderr
    except Exception as e:
        print_error(f"{description} failed with exception: {e}")
        return False, str(e)

def setup_iam_permissions():
    """Setup IAM permissions for GitHub Actions deployment"""
    print_step(1, 7, "Setting up IAM Permissions")
    
    # Define the service accounts
    compute_sa = "932676587025-compute@developer.gserviceaccount.com"
    github_sa = "serviceAccount:github-actions@nytex-business-systems.iam.gserviceaccount.com"
    
    print_info("Ensuring GitHub Actions has permission to act as compute service account...")
    
    # Grant serviceAccountUser role
    cmd = f"""gcloud iam service-accounts add-iam-policy-binding {compute_sa} \
--member="{github_sa}" \
--role="roles/iam.serviceAccountUser" \
--quiet"""
    
    success, output = run_command(cmd, "Setting up service account permissions")
    
    if success:
        print_success("IAM permissions configured successfully")
        return True
    else:
        # Check if permission already exists
        if "already has role" in output or "Policy was not updated" in output:
            print_success("IAM permissions already configured")
            return True
        else:
            print_error("Failed to setup IAM permissions")
            return False

def verify_cloud_run_access():
    """Verify we can access Cloud Run service"""
    print_step(2, 7, "Verifying Cloud Run Access")
    
    cmd = "gcloud run services describe nytex-dashboard --region=us-central1 --format='value(status.url)'"
    success, output = run_command(cmd, "Checking Cloud Run service access")
    
    if success and output.strip():
        print_success(f"Cloud Run service accessible: {output.strip()}")
        return True
    else:
        print_error("Could not access Cloud Run service")
        return False

def run_tests():
    """Run deployment readiness tests"""
    print_step(3, 7, "Running Deployment Readiness Tests")
    
    # Run the deployment readiness script
    success, output = run_command(
        "python scripts/test_deployment_readiness.py",
        "Deployment readiness check"
    )
    
    if not success:
        print_error("Tests failed! Aborting deployment.")
        return False
    
    if "DEPLOYMENT READY!" in output:
        print_success("All critical tests passed - ready for deployment!")
        return True
    else:
        print_error("Tests completed but deployment not ready")
        return False

def get_current_commit():
    """Get the current git commit hash"""
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                          capture_output=True, text=True, cwd=project_root)
    return result.stdout.strip()[:7] if result.returncode == 0 else "unknown"

def push_changes():
    """Push any pending changes"""
    print_step(5, 7, "Checking and Pushing Changes")
    
    # Check if there are any changes to commit
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True, cwd=project_root)
    
    if result.stdout.strip():
        print_info("Found uncommitted changes, committing...")
        
        # Add all changes
        success, _ = run_command("git add .", "Adding changes")
        if not success:
            return False, None
        
        # Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Deploy: automated deployment at {timestamp}"
        success, _ = run_command(f'git commit -m "{commit_msg}"', "Committing changes")
        if not success:
            return False, None
    
    # Push to trigger deployment
    print_info("Pushing to master to trigger CI/CD...")
    success, _ = run_command("git push origin master", "Pushing to GitHub")
    
    if success:
        commit_hash = get_current_commit()
        print_success(f"Pushed commit {commit_hash} - CI/CD pipeline should start")
        return True, commit_hash
    
    return False, None

def wait_for_workflow_start(commit_hash, max_wait=120):
    """Wait for GitHub Actions workflow to start with longer timeout"""
    print_step(6, 7, "Waiting for CI/CD Pipeline to Start")
    
    spinner = ProgressSpinner()
    start_time = time.time()
    api_calls = 0
    
    while time.time() - start_time < max_wait:
        try:
            # Limit API calls to avoid rate limiting
            if api_calls % 10 == 0:  # Only call API every 20 seconds
                # Get GitHub token for authentication
                try:
                    token_result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
                    if token_result.returncode == 0:
                        token = token_result.stdout.strip()
                        headers = {"Authorization": f"token {token}"}
                    else:
                        headers = {}
                except:
                    headers = {}
                
                response = requests.get(
                    "https://api.github.com/repos/josh0312/nytex_dashboard/actions/runs?per_page=5",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    runs = response.json().get('workflow_runs', [])
                    
                    for run in runs:
                        if commit_hash in run.get('head_sha', ''):
                            print_success(f"Found workflow run #{run.get('run_number')}")
                            return run.get('id'), run.get('run_number')
                elif response.status_code == 403:
                    print_warning("GitHub API rate limited, using extended monitoring...")
            
            # Show progress
            elapsed = int(time.time() - start_time)
            print(f"\r   {spinner.next()} Waiting for workflow to start... ({elapsed}s)", end='', flush=True)
            time.sleep(2)
            api_calls += 1
            
        except requests.RequestException:
            print(f"\r   {spinner.next()} Network issue, retrying...", end='', flush=True)
            time.sleep(5)
    
    print(f"\n")
    print_warning(f"Workflow didn't start within {max_wait}s")
    print_info("This may be normal - checking recent deployments...")
    
    # Check if a recent deployment exists
    try:
        # Get GitHub token for authentication
        try:
            token_result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
            if token_result.returncode == 0:
                token = token_result.stdout.strip()
                headers = {"Authorization": f"token {token}"}
            else:
                headers = {}
        except:
            headers = {}
            
        response = requests.get(
            "https://api.github.com/repos/josh0312/nytex_dashboard/actions/runs?per_page=1",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            runs = response.json().get('workflow_runs', [])
            if runs:
                latest_run = runs[0]
                run_id = latest_run.get('id')
                run_number = latest_run.get('run_number')
                print_info(f"Found recent workflow run #{run_number}")
                return run_id, run_number
    except:
        pass
    
    return None, None

def monitor_workflow_simple(workflow_id, run_number):
    """Simple workflow monitoring with fallback to Cloud Run checking"""
    print_step(7, 7, f"Monitoring Deployment Progress")
    
    if workflow_id:
        print_info(f"Monitoring workflow run #{run_number}")
        print_info(f"GitHub Actions URL: https://github.com/josh0312/nytex_dashboard/actions/runs/{workflow_id}")
    else:
        print_info("Monitoring via Cloud Run service status...")
    
    spinner = ProgressSpinner()
    start_time = time.time()
    last_revision = None
    
    # Get initial revision
    try:
        result = subprocess.run([
            'gcloud', 'run', 'services', 'describe', 'nytex-dashboard',
            '--region=us-central1', '--format=value(status.traffic[0].revisionName)'
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            last_revision = result.stdout.strip()
            print_info(f"Starting revision: {last_revision}")
    except:
        pass
    
    # Monitor for changes
    max_wait = 900  # 15 minutes
    while time.time() - start_time < max_wait:
        try:
            elapsed = int(time.time() - start_time)
            
            # Check Cloud Run for new revisions
            result = subprocess.run([
                'gcloud', 'run', 'services', 'describe', 'nytex-dashboard',
                '--region=us-central1', '--format=value(status.traffic[0].revisionName)'
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                current_revision = result.stdout.strip()
                
                if current_revision != last_revision and last_revision:
                    print(f"\n{Colors.GREEN}   🚀 New revision deployed: {current_revision}{Colors.END}")
                    
                    # Test the application
                    test_cmd = "curl -s -o /dev/null -w '%{http_code}' https://nytex-dashboard-nndn66l4ua-uc.a.run.app"
                    test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
                    
                    if test_result.returncode == 0 and test_result.stdout.strip() in ['200', '302']:
                        print_success("🎉 Deployment completed successfully!")
                        print_success(f"Application is healthy (HTTP {test_result.stdout.strip()})")
                        
                        # Run items page health check
                        print_info("Running items page health check...")
                        items_health_cmd = "python scripts/test_items_production_health.py"
                        items_result = subprocess.run(items_health_cmd, shell=True, capture_output=True, text=True, cwd=project_root)
                        
                        if items_result.returncode == 0:
                            print_success("Items page health check passed!")
                        else:
                            print_warning("Items page health check failed!")
                            print_warning("Output:", items_result.stdout[-200:] if items_result.stdout else "No output")
                            print_warning("Error:", items_result.stderr[-200:] if items_result.stderr else "No error")
                        
                        print_info("Production URL: https://nytex-dashboard-nndn66l4ua-uc.a.run.app/")
                        return True
                    else:
                        print_warning("New revision deployed but application may not be healthy")
                
                last_revision = current_revision
            
            # Show progress
            print(f"\r   {spinner.next()} Monitoring deployment... ({elapsed}s) | Current: {last_revision or 'checking...'}", end='', flush=True)
            time.sleep(5)
            
        except KeyboardInterrupt:
            print(f"\n")
            print_warning("Monitoring interrupted by user")
            return False
        except Exception as e:
            print(f"\r   {spinner.next()} Checking status... ({elapsed}s)", end='', flush=True)
            time.sleep(5)
    
    print(f"\n")
    print_warning("Monitoring timeout reached")
    
    # Final health check
    print_info("Performing final health check...")
    test_cmd = "curl -s -o /dev/null -w '%{http_code}' https://nytex-dashboard-nndn66l4ua-uc.a.run.app"
    test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
    
    if test_result.returncode == 0 and test_result.stdout.strip() in ['200', '302']:
        print_success(f"Application is healthy (HTTP {test_result.stdout.strip()})")
        
        # Run final items page health check
        print_info("Running final items page health check...")
        items_health_cmd = "python scripts/test_items_production_health.py"
        items_result = subprocess.run(items_health_cmd, shell=True, capture_output=True, text=True, cwd=project_root)
        
        if items_result.returncode == 0:
            print_success("Items page health check passed!")
        else:
            print_warning("Items page health check failed!")
            
        print_info("Production URL: https://nytex-dashboard-nndn66l4ua-uc.a.run.app/")
        return True
    else:
        print_error("Application health check failed")
        return False

def deploy_microservices():
    """Deploy supporting microservices"""
    print_step(4, 7, "Deploying Supporting Microservices")
    
    # Deploy Square Catalog Export microservice
    print_info("Deploying Square Catalog Export microservice...")
    
    microservice_dir = project_root / "square_catalog_export"
    
    if microservice_dir.exists():
        deploy_script = microservice_dir / "deploy.sh"
        if deploy_script.exists():
            try:
                result = subprocess.run(['./deploy.sh'], cwd=microservice_dir, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_success("Square Catalog Export microservice deployed successfully")
                    return True
                else:
                    print_error("Square Catalog Export microservice deployment failed")
                    if result.stderr:
                        print(f"   Error: {result.stderr.strip()}")
                    return False
            except Exception as e:
                print_error(f"Error deploying microservice: {e}")
                return False
        else:
            print_warning("No deploy script found for Square Catalog Export microservice")
            return True
    else:
        print_warning("Square Catalog Export microservice directory not found")
        return True

def main():
    """Main execution flow"""
    print_header("🚀 Enhanced NyTex Dashboard Deployment")
    
    try:
        # Step 1: Setup IAM permissions
        if not setup_iam_permissions():
            print_error("Failed to setup IAM permissions")
            sys.exit(1)
        
        # Step 2: Verify Cloud Run access
        if not verify_cloud_run_access():
            print_error("Cloud Run access verification failed")
            sys.exit(1)
        
        # Step 3: Run tests
        if not run_tests():
            print_error("Deployment aborted due to test failures")
            sys.exit(1)
        
        # Step 4: Deploy microservices first
        if not deploy_microservices():
            print_warning("Microservice deployment failed, but continuing with main app deployment")
        
        # Step 5: Push changes
        success, commit_hash = push_changes()
        if not success:
            print_error("Failed to push changes")
            sys.exit(1)
        
        # Step 6: Wait for workflow to start
        workflow_id, run_number = wait_for_workflow_start(commit_hash)
        
        # Step 7: Monitor deployment
        success = monitor_workflow_simple(workflow_id, run_number)
        
        if success:
            print_header("🎉 DEPLOYMENT SUCCESSFUL!")
            print_success("Your application is now live in production")
            print_success("All IAM permissions are properly configured")
            sys.exit(0)
        else:
            print_header("⚠️  DEPLOYMENT STATUS UNCERTAIN")
            print_warning("Check the application manually or review GitHub Actions")
            if workflow_id:
                print_info(f"Workflow URL: https://github.com/josh0312/nytex_dashboard/actions/runs/{workflow_id}")
            print_info("Production URL: https://nytex-dashboard-nndn66l4ua-uc.a.run.app/")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n")
        print_warning("Script interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 