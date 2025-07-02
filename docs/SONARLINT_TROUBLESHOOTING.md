# SonarLint Troubleshooting Guide

## Java-related Issues

### Problem: SonarLint shows Java errors

SonarLint requires Java to run its analysis engine. If you see Java-related errors, follow these steps:

### Solution Steps

#### 1. Check Java Installation
```powershell
java -version
```
If this fails, Java is not installed or not in PATH.

#### 2. Install Java (if needed)
- Download [OpenJDK 17](https://adoptium.net/temurin/releases/?version=17) or newer
- Install and add to PATH
- Restart Cursor

#### 3. Find Java Home Path
```powershell
java -XshowSettings:properties -version 2>&1 | Select-String "java.home"
```

#### 4. Configure SonarLint in VS Code Settings
Add to `.vscode/settings.json`:
```json
{
    "sonarlint.ls.javaHome": "C:\\Program Files\\Java\\jdk-24",
    "sonarlint.showVerboseOutput": false,
    "sonarlint.showNotifications": "off"
}
```

#### 5. Reinstall SonarLint Extension
```powershell
# Remove extension
cursor --uninstall-extension sonarsource.sonarlint-vscode

# Install extension
cursor --install-extension sonarsource.sonarlint-vscode
```

#### 6. Restart Cursor
After making changes, restart Cursor completely.

### Common Issues

#### Issue: "Java not found"
- **Solution**: Install Java and add to PATH
- **Alternative**: Set `sonarlint.ls.javaHome` in settings

#### Issue: "Java version incompatible"
- **Solution**: Use Java 11 or newer
- **Current**: Java 24.0.1 is compatible

#### Issue: "SonarLint not working"
- **Solution**: Check extension is installed and enabled
- **Command**: `cursor --list-extensions | findstr sonar`

### Verification

To verify SonarLint is working:
1. Open a Python file
2. Make a code quality issue (e.g., unused variable)
3. SonarLint should show warnings/errors

### Current Configuration

- **Java Version**: 24.0.1
- **Java Home**: `C:\Program Files\Java\jdk-24`
- **SonarLint Version**: 4.25.0
- **Status**: ✅ Configured and working

### Disable SonarLint (if needed)

If you want to disable SonarLint completely:
```json
{
    "sonarlint.showNotifications": "off",
    "sonarlint.showVerboseOutput": false
}
```

Or uninstall the extension:
```powershell
cursor --uninstall-extension sonarsource.sonarlint-vscode
```
