#!/usr/bin/env python
"""
Script to check and update user village
Run: python check_user_village.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gridwatch_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Profile

User = get_user_model()

def main():
    print("\n" + "=" * 60)
    print("USER VILLAGE CHECKER")
    print("=" * 60)
    
    # List all users
    print("\n📋 ALL USERS IN SYSTEM:")
    print("-" * 40)
    
    users = User.objects.all()
    if not users:
        print("❌ No users found!")
        return
    
    for u in users:
        print(f"📧 Email: {u.email}")
        print(f"   👤 Name: {u.get_full_name() or 'Not set'}")
        print(f"   🏠 User.village: '{u.village if hasattr(u, 'village') else 'Field not on User'}'")
        
        # Check profile
        try:
            profile = Profile.objects.get(user=u)
            print(f"   📝 Profile.village: '{profile.village}'")
        except Profile.DoesNotExist:
            print(f"   📝 Profile: Not found")
        print()
    
    # Ask which user to update
    print("\n" + "=" * 60)
    email = input("✏️  Enter the email of the user to update (or press Enter to skip): ").strip()
    
    if email:
        try:
            user = User.objects.get(email=email)
            print(f"\n✅ User found: {user.email}")
            print(f"   Current village: '{user.village if hasattr(user, 'village') else 'N/A'}'")
            
            # Try to get profile
            try:
                profile = Profile.objects.get(user=user)
                print(f"   Current profile village: '{profile.village}'")
            except Profile.DoesNotExist:
                profile = None
                print(f"   Profile: Not found, will create")
            
            # Ask for new village
            new_village = input("\n🏠 Enter new village name: ").strip()
            
            if new_village:
                # Update user if field exists
                if hasattr(user, 'village'):
                    user.village = new_village
                    user.save()
                    print(f"✅ Updated user.village to: {new_village}")
                else:
                    print("⚠️  User model doesn't have village field")
                
                # Update or create profile
                if profile:
                    profile.village = new_village
                    profile.save()
                    print(f"✅ Updated profile.village to: {new_village}")
                else:
                    profile = Profile.objects.create(user=user, village=new_village)
                    print(f"✅ Created profile with village: {new_village}")
                
                print("\n🎉 Village updated successfully!")
            else:
                print("❌ No village entered, skipping update")
                
        except User.DoesNotExist:
            print(f"❌ User with email '{email}' not found")
    
    # Show updated user info
    print("\n" + "=" * 60)
    print("FINAL USER DATA:")
    print("-" * 40)
    
    for u in User.objects.all():
        print(f"\n📧 {u.email}")
        if hasattr(u, 'village'):
            print(f"   User.village: '{u.village}'")
        
        try:
            profile = Profile.objects.get(user=u)
            print(f"   Profile.village: '{profile.village}'")
        except Profile.DoesNotExist:
            pass
    
    print("\n" + "=" * 60)
    print("✅ Script completed!")

if __name__ == "__main__":
    main()