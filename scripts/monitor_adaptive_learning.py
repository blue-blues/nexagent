"""
Monitoring script for the Adaptive Learning System.

This script monitors the health and performance of the Adaptive Learning System
and sends alerts if any issues are detected.
"""

import os
import sys
import time
import json
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import AdaptiveLearningSystem
from app.logger import logger


class AdaptiveLearningMonitor:
    """
    Monitor for the Adaptive Learning System.
    
    This class provides methods for:
    1. Checking the health of the learning system
    2. Monitoring performance metrics
    3. Detecting anomalies
    4. Sending alerts
    """
    
    def __init__(self, state_dir: str, config_file: str = None):
        """
        Initialize the monitor.
        
        Args:
            state_dir: Directory where the learning system state is stored
            config_file: Optional path to a configuration file
        """
        self.state_dir = state_dir
        self.config = self._load_config(config_file)
        self.learning_system = None
        self.last_check_time = None
        self.alerts = []
    
    def _load_config(self, config_file: str = None) -> dict:
        """
        Load the configuration from a file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            Dictionary with the configuration
        """
        # Default configuration
        default_config = {
            "check_interval_minutes": 60,
            "thresholds": {
                "success_rate": 0.7,
                "execution_time": 10.0,
                "storage_size_mb": 1000,
                "interaction_count": 10000
            },
            "alerts": {
                "enabled": False,
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "username": "user@example.com",
                    "password": "password",
                    "from_address": "alerts@example.com",
                    "to_addresses": ["admin@example.com"]
                }
            }
        }
        
        # If no config file is provided, use the default configuration
        if not config_file:
            return default_config
        
        # Load the configuration from the file
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            # Merge with default configuration
            merged_config = default_config.copy()
            merged_config.update(config)
            
            return merged_config
        
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return default_config
    
    def initialize(self) -> bool:
        """
        Initialize the learning system.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Create the learning system
            self.learning_system = AdaptiveLearningSystem()
            
            # Load the state if it exists
            try:
                self.learning_system.load_state(self.state_dir)
                logger.info(f"Loaded learning system state from {self.state_dir}")
            except Exception as e:
                logger.error(f"Error loading learning system state: {str(e)}")
                return False
            
            # Set the last check time
            self.last_check_time = datetime.now()
            
            return True
        
        except Exception as e:
            logger.error(f"Error initializing learning system: {str(e)}")
            return False
    
    def check_health(self) -> dict:
        """
        Check the health of the learning system.
        
        Returns:
            Dictionary with health information
        """
        if not self.learning_system:
            if not self.initialize():
                return {
                    "status": "error",
                    "message": "Failed to initialize learning system",
                    "timestamp": datetime.now().isoformat()
                }
        
        try:
            # Get statistics
            stats = self.learning_system.memory_store.get_statistics()
            
            # Check storage size
            storage_size = self._get_storage_size()
            
            # Check if any thresholds are exceeded
            issues = []
            
            if stats.get("success_rate", 1.0) < self.config["thresholds"]["success_rate"]:
                issues.append(f"Success rate ({stats.get('success_rate', 0) * 100:.1f}%) is below threshold ({self.config['thresholds']['success_rate'] * 100:.1f}%)")
            
            if stats.get("avg_execution_time", 0.0) > self.config["thresholds"]["execution_time"]:
                issues.append(f"Average execution time ({stats.get('avg_execution_time', 0):.2f}s) is above threshold ({self.config['thresholds']['execution_time']:.2f}s)")
            
            if storage_size > self.config["thresholds"]["storage_size_mb"]:
                issues.append(f"Storage size ({storage_size:.1f} MB) is above threshold ({self.config['thresholds']['storage_size_mb']} MB)")
            
            if stats.get("total_count", 0) > self.config["thresholds"]["interaction_count"]:
                issues.append(f"Interaction count ({stats.get('total_count', 0)}) is above threshold ({self.config['thresholds']['interaction_count']})")
            
            # Determine status
            status = "healthy"
            if issues:
                status = "warning"
            
            # Create health report
            health = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "statistics": stats,
                "storage_size_mb": storage_size,
                "issues": issues
            }
            
            # Send alerts if there are issues
            if issues and self.config["alerts"]["enabled"]:
                self._send_alert("Health Check Warning", "\n".join(issues))
            
            return health
        
        except Exception as e:
            logger.error(f"Error checking health: {str(e)}")
            
            return {
                "status": "error",
                "message": f"Error checking health: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_storage_size(self) -> float:
        """
        Get the size of the learning system storage in MB.
        
        Returns:
            Size in MB
        """
        try:
            # Get the size of the state directory
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.state_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            
            # Convert to MB
            return total_size / (1024 * 1024)
        
        except Exception as e:
            logger.error(f"Error getting storage size: {str(e)}")
            return 0.0
    
    def monitor_performance(self) -> dict:
        """
        Monitor the performance of the learning system.
        
        Returns:
            Dictionary with performance information
        """
        if not self.learning_system:
            if not self.initialize():
                return {
                    "status": "error",
                    "message": "Failed to initialize learning system",
                    "timestamp": datetime.now().isoformat()
                }
        
        try:
            # Calculate the time since the last check
            now = datetime.now()
            time_since_last_check = now - self.last_check_time if self.last_check_time else timedelta(days=1)
            days_since_last_check = time_since_last_check.total_seconds() / (24 * 60 * 60)
            
            # Analyze performance
            analysis = self.learning_system.analyze_performance(days=max(1, int(days_since_last_check)))
            
            # Get improvement priorities
            priorities = self.learning_system.get_improvement_priorities()
            
            # Check for high-priority issues
            high_priority_issues = []
            
            for task_type in priorities.get("task_types", []):
                if task_type.get("priority") == "high":
                    high_priority_issues.append(f"Task type '{task_type['task_type']}' has high negative feedback ({task_type['negative_rate'] * 100:.1f}%)")
            
            for tool in priorities.get("tools", []):
                if tool.get("priority") == "high":
                    high_priority_issues.append(f"Tool '{tool['tool']}' has high negative feedback ({tool['negative_rate'] * 100:.1f}%)")
            
            # Create performance report
            performance = {
                "timestamp": now.isoformat(),
                "analysis": analysis,
                "priorities": priorities,
                "high_priority_issues": high_priority_issues
            }
            
            # Send alerts if there are high-priority issues
            if high_priority_issues and self.config["alerts"]["enabled"]:
                self._send_alert("Performance Monitoring Alert", "\n".join(high_priority_issues))
            
            # Update the last check time
            self.last_check_time = now
            
            return performance
        
        except Exception as e:
            logger.error(f"Error monitoring performance: {str(e)}")
            
            return {
                "status": "error",
                "message": f"Error monitoring performance: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def detect_anomalies(self) -> dict:
        """
        Detect anomalies in the learning system.
        
        Returns:
            Dictionary with anomaly information
        """
        if not self.learning_system:
            if not self.initialize():
                return {
                    "status": "error",
                    "message": "Failed to initialize learning system",
                    "timestamp": datetime.now().isoformat()
                }
        
        try:
            # Get statistics
            stats = self.learning_system.memory_store.get_statistics()
            
            # Get strengths and weaknesses
            strengths_and_weaknesses = self.learning_system.identify_strengths_and_weaknesses()
            
            # Detect anomalies
            anomalies = []
            
            # Check for sudden drops in success rate
            if "success_rate_history" in stats:
                history = stats["success_rate_history"]
                if len(history) >= 2:
                    current_rate = history[-1]["value"]
                    previous_rate = history[-2]["value"]
                    
                    if current_rate < previous_rate * 0.8:  # 20% drop
                        anomalies.append(f"Sudden drop in success rate from {previous_rate * 100:.1f}% to {current_rate * 100:.1f}%")
            
            # Check for sudden increases in execution time
            if "execution_time_history" in stats:
                history = stats["execution_time_history"]
                if len(history) >= 2:
                    current_time = history[-1]["value"]
                    previous_time = history[-2]["value"]
                    
                    if current_time > previous_time * 1.5:  # 50% increase
                        anomalies.append(f"Sudden increase in execution time from {previous_time:.2f}s to {current_time:.2f}s")
            
            # Check for task types with very low success rates
            for weakness in strengths_and_weaknesses.get("weaknesses", []):
                if weakness.get("success_rate", 1.0) < 0.5:  # Less than 50% success
                    anomalies.append(f"Task type '{weakness['task_type']}' has very low success rate ({weakness['success_rate'] * 100:.1f}%)")
            
            # Create anomaly report
            anomaly_report = {
                "timestamp": datetime.now().isoformat(),
                "anomalies": anomalies
            }
            
            # Send alerts if there are anomalies
            if anomalies and self.config["alerts"]["enabled"]:
                self._send_alert("Anomaly Detection Alert", "\n".join(anomalies))
            
            return anomaly_report
        
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            
            return {
                "status": "error",
                "message": f"Error detecting anomalies: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _send_alert(self, subject: str, message: str) -> bool:
        """
        Send an alert.
        
        Args:
            subject: Alert subject
            message: Alert message
            
        Returns:
            True if the alert was sent successfully, False otherwise
        """
        # Add the alert to the list
        self.alerts.append({
            "subject": subject,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # If email alerts are not enabled, just log the alert
        if not self.config["alerts"]["email"]["enabled"]:
            logger.warning(f"Alert: {subject} - {message}")
            return True
        
        try:
            # Create the email
            email = MIMEMultipart()
            email["From"] = self.config["alerts"]["email"]["from_address"]
            email["To"] = ", ".join(self.config["alerts"]["email"]["to_addresses"])
            email["Subject"] = f"Nexagent Alert: {subject}"
            
            # Add the message
            email.attach(MIMEText(message, "plain"))
            
            # Connect to the SMTP server
            server = smtplib.SMTP(
                self.config["alerts"]["email"]["smtp_server"],
                self.config["alerts"]["email"]["smtp_port"]
            )
            server.starttls()
            server.login(
                self.config["alerts"]["email"]["username"],
                self.config["alerts"]["email"]["password"]
            )
            
            # Send the email
            server.send_message(email)
            server.quit()
            
            logger.info(f"Sent alert email: {subject}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending alert email: {str(e)}")
            return False
    
    def run_checks(self) -> dict:
        """
        Run all checks.
        
        Returns:
            Dictionary with check results
        """
        # Clear alerts
        self.alerts = []
        
        # Run checks
        health = self.check_health()
        performance = self.monitor_performance()
        anomalies = self.detect_anomalies()
        
        # Create report
        report = {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "performance": performance,
            "anomalies": anomalies,
            "alerts": self.alerts
        }
        
        return report
    
    def save_report(self, report: dict, report_dir: str) -> str:
        """
        Save a report to a file.
        
        Args:
            report: The report to save
            report_dir: Directory to save the report to
            
        Returns:
            Path to the saved report
        """
        try:
            # Create the report directory if it doesn't exist
            os.makedirs(report_dir, exist_ok=True)
            
            # Create the report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"monitoring_report_{timestamp}.json"
            filepath = os.path.join(report_dir, filename)
            
            # Save the report
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Saved monitoring report to {filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            return ""


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Monitor the Adaptive Learning System")
    parser.add_argument("--state-dir", type=str, default=os.path.join(os.path.expanduser("~"), ".nexagent", "learning_state"),
                        help="Directory where the learning system state is stored")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to a configuration file")
    parser.add_argument("--report-dir", type=str, default=os.path.join(os.path.expanduser("~"), ".nexagent", "monitoring"),
                        help="Directory to save monitoring reports to")
    
    args = parser.parse_args()
    
    # Create the monitor
    monitor = AdaptiveLearningMonitor(args.state_dir, args.config)
    
    # Run checks
    report = monitor.run_checks()
    
    # Save the report
    monitor.save_report(report, args.report_dir)
    
    # Print a summary
    print(f"=== Adaptive Learning System Monitoring Report ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Health Status: {report['health']['status']}")
    
    if report['health']['issues']:
        print(f"\nHealth Issues:")
        for issue in report['health']['issues']:
            print(f"- {issue}")
    
    if report['anomalies']['anomalies']:
        print(f"\nAnomalies Detected:")
        for anomaly in report['anomalies']['anomalies']:
            print(f"- {anomaly}")
    
    if report['performance']['high_priority_issues']:
        print(f"\nHigh Priority Issues:")
        for issue in report['performance']['high_priority_issues']:
            print(f"- {issue}")
    
    if report['alerts']:
        print(f"\nAlerts Sent:")
        for alert in report['alerts']:
            print(f"- {alert['subject']}: {alert['message']}")
    
    print(f"\nFull report saved to {args.report_dir}")


if __name__ == "__main__":
    main()
