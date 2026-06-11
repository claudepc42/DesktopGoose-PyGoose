@echo off
echo Building PyGoose...
pyinstaller PyGoose.spec --noconfirm --clean

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Creating user-editable asset folders...
if not exist "dist\PyGoose\assets\images\memes"         mkdir "dist\PyGoose\assets\images\memes"
if not exist "dist\PyGoose\assets\text\notepad_messages" mkdir "dist\PyGoose\assets\text\notepad_messages"

echo.
echo Done. Distribution is ready at dist\PyGoose\
pause
