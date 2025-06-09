#!/usr/bin/env python3
"""
Interactive credential setup script for D&D Notetaker
Guides users through creating the required .credentials/config.json file
"""

import os
import json
import getpass
import sys
from pathlib import Path


class CredentialSetup:
    def __init__(self):
        self.credentials_dir = Path(".credentials")
        self.config_path = self.credentials_dir / "config.json"
        self.config = {}
        
    def print_header(self):
        """Print welcome header"""
        print("\n" + "="*60)
        print("D&D Notetaker - Credential Setup")
        print("="*60)
        print("\nThis script will help you set up the required credentials")
        print("for the D&D session recording processor.\n")
        
    def ensure_credentials_dir(self):
        """Create .credentials directory if it doesn't exist"""
        if not self.credentials_dir.exists():
            self.credentials_dir.mkdir(mode=0o700)
            print(f"✓ Created {self.credentials_dir} directory")
        else:
            print(f"✓ {self.credentials_dir} directory already exists")
            
    def check_existing_config(self):
        """Check if config already exists and ask about overwriting"""
        if self.config_path.exists():
            print(f"\n⚠️  Config file already exists at {self.config_path}")
            response = input("Do you want to overwrite it? (y/N): ").strip().lower()
            if response != 'y':
                print("Keeping existing configuration.")
                # Load and display existing config
                with open(self.config_path, 'r') as f:
                    existing = json.load(f)
                print("\nExisting configuration (passwords hidden):")
                self.display_config(existing, hide_passwords=True)
                
                response = input("\nDo you want to update specific values? (y/N): ").strip().lower()
                if response == 'y':
                    self.config = existing
                    return True
                else:
                    print("Setup cancelled.")
                    sys.exit(0)
        return False
        
    def setup_email_credentials(self, update_mode=False):
        """Set up email/IMAP credentials"""
        print("\n" + "-"*40)
        print("Email Configuration (for downloading recordings)")
        print("-"*40)
        
        if update_mode and 'email' in self.config:
            print("Current email configuration:")
            self.display_config({'email': self.config['email']}, hide_passwords=True)
            if input("Update email settings? (y/N): ").strip().lower() != 'y':
                return
        
        print("\nFor Gmail, you'll need an App Password:")
        print("1. Go to https://myaccount.google.com/apppasswords")
        print("2. Generate an app-specific password")
        print("3. Use that password here (not your regular Gmail password)\n")
        
        email_config = {}
        
        # Email address
        default_email = self.config.get('email', {}).get('email', '') if update_mode else ''
        email = input(f"Email address{f' [{default_email}]' if default_email else ''}: ").strip()
        if not email and default_email:
            email = default_email
        email_config['email'] = email
        
        # Password
        print("App password (input hidden): ", end='', flush=True)
        password = getpass.getpass('')
        if not password and update_mode:
            password = self.config.get('email', {}).get('password', '')
            print("(keeping existing password)")
        email_config['password'] = password
        
        # IMAP server
        default_imap = self.config.get('email', {}).get('imap_server', 'imap.gmail.com') if update_mode else 'imap.gmail.com'
        imap = input(f"IMAP server [{default_imap}]: ").strip()
        if not imap:
            imap = default_imap
        email_config['imap_server'] = imap
        
        self.config['email'] = email_config
        
    def setup_openai_credentials(self, update_mode=False):
        """Set up OpenAI API credentials"""
        print("\n" + "-"*40)
        print("OpenAI Configuration (for transcription and processing)")
        print("-"*40)
        
        if update_mode and 'openai_api_key' in self.config:
            print("Current OpenAI configuration: API key is set")
            if input("Update OpenAI API key? (y/N): ").strip().lower() != 'y':
                return
        
        print("\nTo get an OpenAI API key:")
        print("1. Go to https://platform.openai.com/api-keys")
        print("2. Create a new API key")
        print("3. Copy the key (it won't be shown again)\n")
        
        print("OpenAI API key (input hidden): ", end='', flush=True)
        api_key = getpass.getpass('')
        
        if not api_key and update_mode:
            api_key = self.config.get('openai_api_key', '')
            print("(keeping existing API key)")
        
        self.config['openai_api_key'] = api_key
        
    def setup_google_auth(self):
        """Guide for Google service account setup"""
        print("\n" + "-"*40)
        print("Google Service Account Setup (for Drive and Docs access)")
        print("-"*40)
        
        self.setup_service_account()
    
    def setup_service_account(self):
        """Guide for service account setup"""
        print("\n" + "="*50)
        print("SERVICE ACCOUNT SETUP")
        print("="*50)
        
        print("\n1. Go to https://console.cloud.google.com/")
        print("2. Select your project or create a new one")
        print("3. Enable required APIs:")
        print("   - APIs & Services > Enable APIs")
        print("   - Enable: Google Drive API")
        print("   - Enable: Google Docs API")
        
        print("\n4. Create Service Account:")
        print("   - Go to 'IAM & Admin' > 'Service Accounts'")
        print("   - Click 'Create Service Account'")
        print("   - Name: 'dnd-notetaker' (or similar)")
        print("   - Description: 'Service account for D&D session processor'")
        
        print("\n5. Grant Permissions:")
        print("   - Role 1: 'Viewer' (for Drive read access)")
        print("   - Role 2: 'Google Docs Editor' (to create documents)")
        print("   - Click 'Continue'")
        
        print("\n6. Create Key:")
        print("   - Click 'Create Key'")
        print("   - Choose JSON format")
        print("   - Download the file")
        print(f"   - Save as: {self.credentials_dir}/service_account.json")
        
        print("\n7. Share Access (if needed):")
        print("   - Copy the service account email from the JSON file")
        print("   - Share your Google Drive folders with this email")
        print("   - Grant 'Viewer' permission")
        
        input("\nPress Enter when you've completed these steps...")
        
        # Check if service_account.json exists
        sa_path = self.credentials_dir / "service_account.json"
        if sa_path.exists():
            print(f"\n✓ Found {sa_path}")
            # Validate it's a service account file
            try:
                with open(sa_path) as f:
                    data = json.load(f)
                    if data.get('type') == 'service_account':
                        print("✓ Valid service account file")
                        print(f"✓ Service account email: {data.get('client_email', 'unknown')}")
                    else:
                        print("⚠️  File doesn't appear to be a service account key")
            except Exception as e:
                print(f"⚠️  Error reading service account file: {e}")
        else:
            print(f"\n⚠️  {sa_path} not found")
            print("   You'll need to add this file before running the processor")
    
            
    def display_config(self, config=None, hide_passwords=False):
        """Display configuration (with option to hide passwords)"""
        if config is None:
            config = self.config
            
        display_config = json.loads(json.dumps(config))  # Deep copy
        
        if hide_passwords:
            if 'email' in display_config and 'password' in display_config['email']:
                display_config['email']['password'] = "***hidden***"
            if 'openai_api_key' in display_config:
                # Show first 6 and last 4 characters
                key = display_config['openai_api_key']
                if len(key) > 10:
                    display_config['openai_api_key'] = f"{key[:6]}...{key[-4:]}"
                else:
                    display_config['openai_api_key'] = "***hidden***"
                    
        print(json.dumps(display_config, indent=2))
        
    def save_config(self):
        """Save configuration to file"""
        try:
            # Set restrictive permissions (owner read/write only)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            # Ensure file has restricted permissions
            os.chmod(self.config_path, 0o600)
            
            print(f"\n✓ Configuration saved to {self.config_path}")
            print("  (with restricted permissions for security)")
            
        except Exception as e:
            print(f"\n❌ Error saving configuration: {e}")
            sys.exit(1)
            
    def verify_setup(self):
        """Verify all required files are in place"""
        print("\n" + "-"*40)
        print("Setup Verification")
        print("-"*40)
        
        all_good = True
        
        # Check config.json
        if self.config_path.exists():
            print(f"✓ {self.config_path} exists")
        else:
            print(f"❌ {self.config_path} missing")
            all_good = False
            
        # Check Google authentication file
        service_account = self.credentials_dir / "service_account.json"
        
        if service_account.exists():
            print(f"✓ {service_account} exists")
        else:
            print(f"⚠️  No Google authentication found")
            print(f"   Need {service_account}")
            
        # Check config content
        if all_good:
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                required_fields = [
                    ('email.email', lambda c: c.get('email', {}).get('email')),
                    ('email.password', lambda c: c.get('email', {}).get('password')),
                    ('email.imap_server', lambda c: c.get('email', {}).get('imap_server')),
                    ('openai_api_key', lambda c: c.get('openai_api_key'))
                ]
                
                for field_name, getter in required_fields:
                    if getter(config):
                        print(f"✓ {field_name} is set")
                    else:
                        print(f"❌ {field_name} is missing")
                        all_good = False
                        
            except Exception as e:
                print(f"❌ Error reading config: {e}")
                all_good = False
                
        return all_good
        
    def run(self):
        """Run the interactive setup"""
        self.print_header()
        self.ensure_credentials_dir()
        
        # Check for existing config
        update_mode = self.check_existing_config()
        
        # Set up each credential type
        self.setup_email_credentials(update_mode)
        self.setup_openai_credentials(update_mode)
        
        # Save configuration
        self.save_config()
        
        # Display saved configuration
        print("\n" + "-"*40)
        print("Saved Configuration")
        print("-"*40)
        self.display_config(hide_passwords=True)
        
        # Guide for Google authentication
        if not update_mode or input("\nReview Google authentication setup instructions? (y/N): ").strip().lower() == 'y':
            self.setup_google_auth()
        
        # Verify setup
        if self.verify_setup():
            print("\n✅ Setup completed successfully!")
            print("\nYou can now run:")
            print("  python main.py process")
            print("\nTo process your first D&D session recording.")
        else:
            print("\n⚠️  Setup incomplete. Please add missing components.")
            
        print("\nTo update credentials later, run this script again.")
        print("="*60 + "\n")


def main():
    """Main entry point"""
    try:
        setup = CredentialSetup()
        setup.run()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()