"""
Quick script to check if production_models.py has syntax errors
Run this from the backend directory: python check_production_models.py
"""

import sys
import os
import django

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

print("Checking production_models.py...")
print("="*60)

try:
    # Try to import the module
    from layers.models import production_models
    
    print("✓ Module loaded successfully")
    print("\nAvailable classes:")
    
    # List all classes in the module
    classes = [name for name in dir(production_models) 
               if not name.startswith('_') and name[0].isupper()]
    
    for cls_name in classes:
        print(f"  - {cls_name}")
    
    # Check for specific models
    required_models = [
        'BillOfMaterials',
        'BOMComponent', 
        'ProductionOrder',
        'ProductionOrderItem',
        'ProductionPhase'
    ]
    
    print("\nChecking required models:")
    missing = []
    for model_name in required_models:
        if hasattr(production_models, model_name):
            print(f"  ✓ {model_name} found")
        else:
            print(f"  ✗ {model_name} MISSING!")
            missing.append(model_name)
    
    if not missing:
        print("\n✓ All required models are present!")
        print("\nYou can now run:")
        print("  python manage.py makemigrations")
        print("  python manage.py migrate")
    else:
        print(f"\n✗ Missing models: {', '.join(missing)}")
    
except SyntaxError as e:
    print(f"✗ Syntax Error in file:")
    print(f"  Line {e.lineno}: {e.msg}")
    print(f"  {e.text}")
    
except ImportError as e:
    print(f"✗ Import Error:")
    print(f"  {str(e)}")
    
except Exception as e:
    print(f"✗ Unexpected Error:")
    print(f"  {type(e).__name__}: {str(e)}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()

print("="*60)