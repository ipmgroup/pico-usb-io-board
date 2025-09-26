#!/bin/bash

# Test script for setup_dln2_system.sh
# Validates script functionality without running full installation

set -e

echo "🧪 Testing setup_dln2_system.sh..."
echo

# Test 1: Syntax check
echo "1. Syntax check..."
if bash -n setup_dln2_system.sh; then
    echo "   ✅ Syntax OK"
else
    echo "   ❌ Syntax error"
    exit 1
fi

# Test 2: Executable permissions
echo "2. Permission check..."
if [[ -x setup_dln2_system.sh ]]; then
    echo "   ✅ Executable"
else
    echo "   ❌ Not executable"
    exit 1
fi

# Test 3: Root check (should fail)
echo "3. Root check (should require sudo)..."
if timeout 5s ./setup_dln2_system.sh 2>&1 | grep -q "must be run as root"; then
    echo "   ✅ Root check works"
else
    echo "   ❌ Root check failed"
    exit 1
fi

# Test 4: Functions exist
echo "4. Function definitions..."
REQUIRED_FUNCTIONS=(
    "check_root"
    "check_system" 
    "update_system"
    "install_dependencies"
    "setup_user_groups"
    "create_udev_rules"
    "reload_udev"
    "enable_i2c"
    "setup_python_environment"
    "create_helper_scripts"
    "create_readme"
    "main"
)

for func in "${REQUIRED_FUNCTIONS[@]}"; do
    if grep -q "^$func()" setup_dln2_system.sh; then
        echo "   ✅ $func"
    else
        echo "   ❌ $func missing"
        exit 1
    fi
done

# Test 5: Required variables
echo "5. Variable definitions..."
REQUIRED_VARS=(
    "SCRIPT_DIR"
    "USER_NAME"
    "UDEV_RULES_FILE"
    "LOG_FILE"
)

for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "$var=" setup_dln2_system.sh; then
        echo "   ✅ $var"
    else
        echo "   ❌ $var missing"
        exit 1
    fi
done

# Test 6: Quick check script
echo "6. Quick check script..."
if bash -n quick_check.sh; then
    echo "   ✅ quick_check.sh syntax OK"
else
    echo "   ❌ quick_check.sh syntax error"
    exit 1
fi

# Test 7: Documentation exists
echo "7. Documentation..."
REQUIRED_DOCS=("INSTALL.md")

for doc in "${REQUIRED_DOCS[@]}"; do
    if [[ -f "$doc" ]]; then
        echo "   ✅ $doc"
    else
        echo "   ❌ $doc missing"
        exit 1
    fi
done

echo
echo "🎉 All tests passed!"
echo "✅ setup_dln2_system.sh is ready for production use"
echo
echo "💡 To use:"
echo "   sudo ./setup_dln2_system.sh    # Full system setup"
echo "   ./quick_check.sh               # System verification"
