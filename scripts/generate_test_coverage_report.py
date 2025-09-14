#!/usr/bin/env python3
"""Generate comprehensive test coverage reports for the microcosting project.

This script generates detailed test coverage reports including:
- Overall coverage statistics
- Coverage by module
- Missing coverage areas
- Coverage trends over time
"""

import subprocess
import sys
import json
import os
from typing import Dict, List, Any
import xml.etree.ElementTree as ET


def run_coverage_analysis() -> Dict[str, Any]:
    """Run pytest with coverage analysis and collect results.
    
    Returns:
        Dictionary containing coverage analysis results
    """
    try:
        # Run pytest with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--cov=src/unimelb_phd_phase_1", 
            "--cov-report=xml:coverage.xml",
            "--cov-report=json:coverage.json",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=0",  # Don't fail if coverage is below threshold
            "tests/"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        print("Coverage analysis completed")
        print(f"Return code: {result.returncode}")
        
        if result.stderr:
            print(f"STDERR: {result.stderr}")
            
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        print(f"Error running coverage analysis: {e}")
        return {"success": False, "error": str(e)}


def parse_coverage_xml(xml_file: str = "coverage.xml") -> Dict[str, Any]:
    """Parse XML coverage report and extract key metrics.
    
    Args:
        xml_file: Path to XML coverage report file
        
    Returns:
        Dictionary containing parsed coverage metrics
    """
    try:
        if not os.path.exists(xml_file):
            return {"error": f"XML file {xml_file} not found"}
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Extract overall coverage metrics
        coverage_elem = root
        line_rate = float(coverage_elem.get("line-rate", 0))
        branch_rate = float(coverage_elem.get("branch-rate", 0))
        lines_covered = int(coverage_elem.get("lines-covered", 0))
        lines_valid = int(coverage_elem.get("lines-valid", 0))
        
        # Extract package information
        packages = []
        packages_elem = root.find("packages")
        if packages_elem is not None:
            for package_elem in packages_elem.findall("package"):
                package_name = package_elem.get("name", "")
                package_line_rate = float(package_elem.get("line-rate", 0))
                
                # Extract class information
                classes = []
                classes_elem = package_elem.find("classes")
                if classes_elem is not None:
                    for class_elem in classes_elem.findall("class"):
                        class_name = class_elem.get("name", "")
                        class_filename = class_elem.get("filename", "")
                        class_line_rate = float(class_elem.get("line-rate", 0))
                        
                        classes.append({
                            "name": class_name,
                            "filename": class_filename,
                            "line_rate": class_line_rate
                        })
                
                packages.append({
                    "name": package_name,
                    "line_rate": package_line_rate,
                    "classes": classes
                })
        
        return {
            "line_rate": line_rate,
            "branch_rate": branch_rate,
            "lines_covered": lines_covered,
            "lines_valid": lines_valid,
            "coverage_percentage": round(line_rate * 100, 2),
            "packages": packages
        }
    except Exception as e:
        return {"error": f"Error parsing XML coverage report: {e}"}


def parse_coverage_json(json_file: str = "coverage.json") -> Dict[str, Any]:
    """Parse JSON coverage report and extract detailed metrics.
    
    Args:
        json_file: Path to JSON coverage report file
        
    Returns:
        Dictionary containing parsed coverage metrics
    """
    try:
        if not os.path.exists(json_file):
            return {"error": f"JSON file {json_file} not found"}
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        return {"error": f"Error parsing JSON coverage report: {e}"}


def generate_coverage_summary(coverage_data: Dict[str, Any]) -> str:
    """Generate a human-readable coverage summary.
    
    Args:
        coverage_data: Coverage data from XML parser
        
    Returns:
        Formatted coverage summary string
    """
    if "error" in coverage_data:
        return f"Error: {coverage_data['error']}"
    
    summary = []
    summary.append("=" * 60)
    summary.append("GENOMICS MICROCOSTING PROJECT - TEST COVERAGE REPORT")
    summary.append("=" * 60)
    summary.append("")
    
    # Overall statistics
    summary.append("OVERALL COVERAGE STATISTICS:")
    summary.append("-" * 30)
    summary.append(f"Lines Covered: {coverage_data['lines_covered']}/{coverage_data['lines_valid']}")
    summary.append(f"Coverage Percentage: {coverage_data['coverage_percentage']:.2f}%")
    summary.append(f"Line Rate: {coverage_data['line_rate']:.4f}")
    summary.append(f"Branch Rate: {coverage_data['branch_rate']:.4f}")
    summary.append("")
    
    # Package-level coverage
    summary.append("PACKAGE-LEVEL COVERAGE:")
    summary.append("-" * 25)
    for package in coverage_data.get("packages", []):
        package_name = package["name"]
        line_rate = package["line_rate"]
        coverage_pct = round(line_rate * 100, 2)
        summary.append(f"{package_name}: {coverage_pct:.2f}%")
        
        # Class-level details
        for class_info in package.get("classes", []):
            class_name = class_info["name"]
            class_rate = class_info["line_rate"]
            class_pct = round(class_rate * 100, 2)
            summary.append(f"  └─ {class_name}: {class_pct:.2f}%")
    summary.append("")
    
    # Coverage assessment
    coverage_pct = coverage_data['coverage_percentage']
    if coverage_pct >= 90:
        assessment = "EXCELLENT - Ready for production"
    elif coverage_pct >= 80:
        assessment = "GOOD - Meets most requirements"
    elif coverage_pct >= 70:
        assessment = "FAIR - Some areas need improvement"
    else:
        assessment = "POOR - Significant coverage gaps"
    
    summary.append("COVERAGE ASSESSMENT:")
    summary.append("-" * 22)
    summary.append(f"Overall Assessment: {assessment}")
    summary.append("")
    
    return "\n".join(summary)


def identify_low_coverage_areas(coverage_data: Dict[str, Any], threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Identify areas with low test coverage.
    
    Args:
        coverage_data: Coverage data from XML parser
        threshold: Coverage threshold (default 80%)
        
    Returns:
        List of low coverage areas
    """
    low_coverage_areas = []
    
    for package in coverage_data.get("packages", []):
        package_name = package["name"]
        package_rate = package["line_rate"]
        
        if package_rate < threshold:
            low_coverage_areas.append({
                "type": "package",
                "name": package_name,
                "coverage_rate": package_rate,
                "coverage_percentage": round(package_rate * 100, 2)
            })
        
        # Check classes within package
        for class_info in package.get("classes", []):
            class_name = class_info["name"]
            class_rate = class_info["line_rate"]
            
            if class_rate < threshold:
                low_coverage_areas.append({
                    "type": "class",
                    "name": f"{package_name}.{class_name}",
                    "coverage_rate": class_rate,
                    "coverage_percentage": round(class_rate * 100, 2)
                })
    
    return low_coverage_areas


def generate_html_report_summary(coverage_data: Dict[str, Any]) -> str:
    """Generate HTML report summary for web viewing.
    
    Args:
        coverage_data: Coverage data from XML parser
        
    Returns:
        HTML formatted summary
    """
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html>")
    html.append("<head>")
    html.append("<title>Test Coverage Report</title>")
    html.append("<style>")
    html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
    html.append("h1, h2 { color: #333; }")
    html.append(".stats { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }")
    html.append(".low-coverage { background: #ffe6e6; padding: 10px; margin: 5px 0; border-left: 4px solid #ff4444; }")
    html.append(".good-coverage { background: #e6ffe6; padding: 10px; margin: 5px 0; border-left: 4px solid #44aa44; }")
    html.append(".metric { font-weight: bold; }")
    html.append("</style>")
    html.append("</head>")
    html.append("<body>")
    html.append("<h1>Genomics Microcosting Project - Test Coverage Report</h1>")
    
    # Overall statistics
    html.append("<div class='stats'>")
    html.append("<h2>Overall Coverage Statistics</h2>")
    html.append(f"<p><span class='metric'>Coverage Percentage:</span> {coverage_data['coverage_percentage']:.2f}%</p>")
    html.append(f"<p><span class='metric'>Lines Covered:</span> {coverage_data['lines_covered']}/{coverage_data['lines_valid']}</p>")
    html.append(f"<p><span class='metric'>Line Rate:</span> {coverage_data['line_rate']:.4f}</p>")
    html.append("</div>")
    
    # Coverage assessment
    coverage_pct = coverage_data['coverage_percentage']
    if coverage_pct >= 90:
        status_class = "good-coverage"
        assessment = "Excellent - Ready for production"
    elif coverage_pct >= 80:
        status_class = "good-coverage"
        assessment = "Good - Meets most requirements"
    else:
        status_class = "low-coverage"
        assessment = "Needs improvement"
    
    html.append(f"<div class='{status_class}'>")
    html.append("<h2>Coverage Assessment</h2>")
    html.append(f"<p>{assessment}</p>")
    html.append("</div>")
    
    # Package details
    html.append("<h2>Package Coverage Details</h2>")
    for package in coverage_data.get("packages", []):
        package_name = package["name"]
        package_rate = package["line_rate"]
        package_pct = round(package_rate * 100, 2)
        
        package_class = "good-coverage" if package_rate >= 0.8 else "low-coverage"
        html.append(f"<div class='{package_class}'>")
        html.append(f"<h3>{package_name}</h3>")
        html.append(f"<p>Coverage: {package_pct:.2f}%</p>")
        html.append("</div>")
    
    html.append("</body>")
    html.append("</html>")
    
    return "\n".join(html)


def main():
    """Main function to generate coverage reports."""
    print("Generating test coverage report...")
    
    # Run coverage analysis
    coverage_result = run_coverage_analysis()
    
    if not coverage_result["success"]:
        print("Coverage analysis failed:")
        if "stdout" in coverage_result:
            print(coverage_result["stdout"])
        if "stderr" in coverage_result:
            print(coverage_result["stderr"])
        return 1
    
    # Parse coverage data
    coverage_data = parse_coverage_xml()
    
    if "error" in coverage_data:
        print(f"Error parsing coverage data: {coverage_data['error']}")
        return 1
    
    # Generate and print summary
    summary = generate_coverage_summary(coverage_data)
    print(summary)
    
    # Identify low coverage areas
    low_coverage_areas = identify_low_coverage_areas(coverage_data)
    if low_coverage_areas:
        print("AREAS NEEDING IMPROVED COVERAGE:")
        print("-" * 35)
        for area in low_coverage_areas:
            print(f"{area['name']}: {area['coverage_percentage']:.2f}%")
        print("")
    
    # Generate HTML report
    html_content = generate_html_report_summary(coverage_data)
    with open("coverage_report.html", "w") as f:
        f.write(html_content)
    
    print("HTML coverage report saved to: coverage_report.html")
    print("Detailed coverage reports saved to: htmlcov/ directory")
    print("Coverage data saved to: coverage.xml, coverage.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())