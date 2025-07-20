#!/usr/bin/env python3
"""
Interface Validation Script
Tests the English localization and modern UX implementation
"""

import os
import re
from pathlib import Path

class InterfaceValidator:
    def __init__(self, static_dir="src/main/resources/static"):
        self.static_dir = Path(static_dir)
        self.issues = []
        self.passed_tests = []
        
    def validate_html_localization(self):
        """Validate HTML file for English localization"""
        html_file = self.static_dir / "index.html"
        
        if not html_file.exists():
            self.issues.append("❌ HTML file not found")
            return
            
        content = html_file.read_text(encoding='utf-8')
        
        # Check for English language declaration
        if 'lang="en"' in content:
            self.passed_tests.append("✅ HTML language set to English")
        else:
            self.issues.append("❌ HTML language not set to English")
            
        # Check for English text content
        english_checks = [
            ("Discover Sacred Fukui", "Hero section has English title"),
            ("Search shrines and temples", "Search section has English text"),
            ("Ask questions about", "AI Q&A section has English text"),
            ("Get Recommendations", "Recommendation section has English text"),
            ("Find Nearby Places", "Location section has English text"),
            ("API Status", "Status section has English text")
        ]
        
        for text, description in english_checks:
            if text in content:
                self.passed_tests.append(f"✅ {description}")
            else:
                self.issues.append(f"❌ Missing: {description}")
                
        # Check for Chinese text (should be minimal/none)
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        chinese_matches = chinese_pattern.findall(content)
        if chinese_matches:
            self.issues.append(f"❌ Found Chinese text: {chinese_matches[:5]}")
        else:
            self.passed_tests.append("✅ No Chinese text found in HTML")
            
        # Check for accessibility features
        accessibility_checks = [
            ('aria-label', "ARIA labels present"),
            ('role=', "ARIA roles present"),
            ('<label', "Form labels present"),
            ('alt=', "Image alt text present")
        ]
        
        for feature, description in accessibility_checks:
            if feature in content:
                self.passed_tests.append(f"✅ {description}")
            else:
                self.issues.append(f"⚠️ Limited: {description}")

    def validate_css_modernization(self):
        """Validate CSS file for modern design patterns"""
        css_file = self.static_dir / "style.css"
        
        if not css_file.exists():
            self.issues.append("❌ CSS file not found")
            return
            
        content = css_file.read_text(encoding='utf-8')
        
        # Check for modern CSS features
        modern_features = [
            (':root', "CSS custom properties (variables)"),
            ('--primary-color', "Color system variables"),
            ('linear-gradient', "Modern gradients"),
            ('@media', "Responsive design"),
            ('transition:', "Smooth animations"),
            ('transform:', "Modern transforms"),
            ('flex', "Flexbox layout"),
            ('grid', "CSS Grid layout")
        ]
        
        for feature, description in modern_features:
            if feature in content:
                self.passed_tests.append(f"✅ {description}")
            else:
                self.issues.append(f"⚠️ Missing: {description}")
                
        # Check for Japan-inspired design
        japan_design = [
            ('--sakura-pink', "Cherry blossom theming"),
            ('--bamboo-green', "Bamboo green theming"),
            ('#c8102e', "Japan flag red color")
        ]
        
        for feature, description in japan_design:
            if feature in content:
                self.passed_tests.append(f"✅ {description}")

    def validate_js_localization(self):
        """Validate JavaScript file for English localization"""
        js_file = self.static_dir / "app.js"
        
        if not js_file.exists():
            self.issues.append("❌ JavaScript file not found")
            return
            
        content = js_file.read_text(encoding='utf-8')
        
        # Check for English text in JS
        english_js_checks = [
            ("API Online", "API status messages in English"),
            ("Please enter search keywords", "Form validation in English"),
            ("Search error occurred", "Error messages in English"),
            ("Location acquired", "Location messages in English"),
            ("showToast", "Toast notification system present"),
            ("addSuggestionPills", "Suggestion pills feature present")
        ]
        
        for text, description in english_js_checks:
            if text in content:
                self.passed_tests.append(f"✅ {description}")
            else:
                self.issues.append(f"❌ Missing: {description}")
                
        # Check for Chinese text in JS
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        chinese_matches = chinese_pattern.findall(content)
        if chinese_matches:
            self.issues.append(f"❌ Found Chinese text in JS: {chinese_matches[:3]}")
        else:
            self.passed_tests.append("✅ No Chinese text found in JavaScript")
            
        # Check for modern UX patterns
        ux_features = [
            ("toast", "Toast notifications"),
            ("suggestion", "Suggestion pills"),
            ("loading-spinner", "Loading states"),
            ("error-message", "Error handling")
        ]
        
        for feature, description in ux_features:
            if feature in content:
                self.passed_tests.append(f"✅ {description}")

    def validate_file_structure(self):
        """Validate overall file structure"""
        required_files = [
            "index.html",
            "style.css", 
            "app.js"
        ]
        
        for filename in required_files:
            file_path = self.static_dir / filename
            if file_path.exists():
                self.passed_tests.append(f"✅ {filename} exists")
                # Check file size (should not be empty)
                if file_path.stat().st_size > 100:
                    self.passed_tests.append(f"✅ {filename} has content")
                else:
                    self.issues.append(f"⚠️ {filename} appears empty")
            else:
                self.issues.append(f"❌ {filename} missing")

    def run_validation(self):
        """Run all validation tests"""
        print("🚀 Starting Interface Validation...")
        print("=" * 50)
        
        self.validate_file_structure()
        self.validate_html_localization()
        self.validate_css_modernization()
        self.validate_js_localization()
        
        print("\n📊 VALIDATION RESULTS")
        print("=" * 50)
        
        print(f"\n✅ PASSED TESTS ({len(self.passed_tests)}):")
        for test in self.passed_tests:
            print(f"  {test}")
            
        if self.issues:
            print(f"\n⚠️ ISSUES FOUND ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  {issue}")
        else:
            print("\n🎉 No issues found!")
            
        # Calculate score
        total_tests = len(self.passed_tests) + len(self.issues)
        if total_tests > 0:
            score = (len(self.passed_tests) / total_tests) * 100
            print(f"\n📈 OVERALL SCORE: {score:.1f}%")
            
            if score >= 90:
                print("🌟 EXCELLENT - Interface ready for production!")
            elif score >= 75:
                print("👍 GOOD - Minor improvements recommended")
            elif score >= 50:
                print("⚠️ NEEDS WORK - Several issues to address")
            else:
                print("❌ CRITICAL - Major issues need fixing")
        
        return len(self.issues) == 0

if __name__ == "__main__":
    validator = InterfaceValidator()
    success = validator.run_validation()
    exit(0 if success else 1)